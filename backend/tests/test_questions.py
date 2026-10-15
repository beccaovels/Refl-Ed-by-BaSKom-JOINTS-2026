"""The AI students: when they ask, answer and react, and how deep a question may go."""

from sqlmodel import select

from app.core.config import settings
from app.models import Question, TranscriptSegment
from app.services import llm, metrics, profiles, questions
from app.services.questions import StudentAnswer, StudentQuestion, StudentReaction

CANNED = [text for text, _ in questions.CANNED_QUESTIONS]


def speak(db, lesson, seq, start_ms, end_ms, text="penjelasan"):
    db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start_ms, end_ms=end_ms, text=text))
    db.commit()


def real_llm(monkeypatch, replies):
    """Pretend a provider is configured. `replies` maps a reply class to what the LLM returns for it."""
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    prompts = []

    def generate(prompt, schema, **kwargs):
        prompts.append(prompt)
        reply = replies[schema]
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(llm, "generate_json", generate)
    return prompts


def kinds(db):
    return [q.kind for q in db.exec(select(Question).order_by(Question.asked_at_ms))]


# --- asking ---


def test_no_question_before_the_interval(db, lesson):
    speak(db, lesson, 0, 0, 30_000)
    assert questions.next_event(db, lesson.id, now_ms=30_000) is None


def test_a_question_comes_after_enough_teaching_in_the_event_shape(db, lesson):
    speak(db, lesson, 0, 0, 40_000)
    speak(db, lesson, 1, 41_000, 80_000)
    event = questions.next_event(db, lesson.id, now_ms=80_000)
    assert event["kind"] == "regular"
    assert set(event) == {
        "id", "kind", "persona", "text", "asked_at_ms", "refers_to_ms", "level", "question_id", "satisfied",
    }  # fmt: skip
    assert event["persona"]["name"] == "Dimas" and event["asked_at_ms"] == 80_000 and event["level"] == 1


def test_question_wording_and_level_come_from_the_llm(db, lesson, monkeypatch):
    prompts = real_llm(monkeypatch, {StudentQuestion: StudentQuestion(text="Kenapa peluangnya setengah?", refers_to_line=1, level=2)})
    speak(db, lesson, 0, 0, 40_000)
    speak(db, lesson, 1, 41_000, 80_000)
    event = questions.next_event(db, lesson.id, now_ms=80_000)
    assert (event["text"], event["refers_to_ms"], event["level"]) == ("Kenapa peluangnya setengah?", 0, 2)
    assert "1. penjelasan\n2. penjelasan" in prompts[0]
    assert "peluang sederhana dari SMP" in prompts[0]  # what this grade already knows
    assert "melempar dua dadu" in prompts[0]  # a sparking question from the teacher's book


def test_provider_failure_falls_back_to_a_canned_question(db, lesson, monkeypatch):
    real_llm(monkeypatch, {StudentQuestion: llm.LLMError("503")})
    speak(db, lesson, 0, 0, 80_000)
    assert questions.next_event(db, lesson.id, now_ms=80_000)["text"] in CANNED


def test_a_repeated_question_is_replaced(db, lesson, monkeypatch):
    # The model proposes a question that was already asked and settled.
    real_llm(monkeypatch, {StudentQuestion: StudentQuestion(text=CANNED[0], refers_to_line=1)})
    first = Question(session_id=lesson.id, kind="regular", text=CANNED[0], asked_at_ms=0, answered_at_ms=0)
    db.add(first)
    db.commit()
    db.add(Question(session_id=lesson.id, kind="reaction", text="Oke.", asked_at_ms=1, reply_to=first.id, satisfied=True))
    db.commit()
    speak(db, lesson, 0, 1_000, 81_000)
    event = questions.next_event(db, lesson.id, now_ms=81_000)
    assert event["kind"] == "regular" and event["text"] == CANNED[1]


# --- depth by grade ---


def test_grade_ten_starts_shallow_and_allows_one_level_three():
    profile = profiles.get("matematika-fase-e")
    assert questions._levels(profile, []) == [1, 2]
    two_asked = [Question(session_id="s", kind="regular", text="a", asked_at_ms=0, level=1)] * 2
    assert questions._levels(profile, two_asked) == [1, 2, 3]
    with_a_three = two_asked + [Question(session_id="s", kind="regular", text="b", asked_at_ms=0, level=3)]
    assert questions._levels(profile, with_a_three) == [1, 2]


def test_a_higher_grade_profile_asks_deeper():
    grade_eleven = {"question_depth": {"first": [2], "later": [2, 3]}}
    assert questions._levels(grade_eleven, []) == [2]
    assert questions._levels(grade_eleven, [Question(session_id="s", kind="regular", text="a", asked_at_ms=0, level=3)] * 4) == [2, 3]
    assert questions._allowed(1, [2, 3]) == 2  # a level the grade does not allow moves to the nearest one
    assert questions._allowed(3, [1, 2]) == 2


def test_the_level_is_kept_within_what_the_grade_allows(db, lesson, monkeypatch):
    real_llm(monkeypatch, {StudentQuestion: StudentQuestion(text="Bagaimana kalau dadunya tiga?", refers_to_line=1, level=3)})
    speak(db, lesson, 0, 0, 80_000)
    assert questions.next_event(db, lesson.id, now_ms=80_000)["level"] == 2  # first question in grade X: 1 or 2


# --- misconception ---


def test_a_documented_misconception_is_asked_once_when_its_topic_comes_up(db, lesson, monkeypatch):
    prompts = real_llm(
        monkeypatch,
        {
            StudentQuestion: StudentQuestion(text="Kalau sudah gambar tiga kali, berikutnya pasti angka ya?", refers_to_line=1, level=1),
            StudentReaction: StudentReaction(satisfied=True, text="Oh, jadi tetap setengah."),
        },
    )
    speak(db, lesson, 0, 0, 80_000, "Kita lempar uang logam, peluang gambar dan angka masing-masing setengah.")
    event = questions.next_event(db, lesson.id, now_ms=80_000)
    assert event["kind"] == "misconception" and event["level"] == 2
    assert "Hasil kejadian sebelumnya dianggap memengaruhi" in prompts[0]  # the book's wording, p. 258

    speak(db, lesson, 1, 81_000, 95_000, "Tidak, setiap lemparan uang logam saling bebas.")
    assert questions.next_event(db, lesson.id, now_ms=95_000)["kind"] == "reaction"
    speak(db, lesson, 2, 96_000, 180_000, "Sekarang uang logam kita lempar lagi dan catat hasilnya.")
    assert questions.next_event(db, lesson.id, now_ms=180_000)["kind"] == "regular"  # never a second misconception


def test_without_the_llm_the_misconception_uses_the_profile_line(db, lesson):
    speak(db, lesson, 0, 0, 80_000, "Sekarang kita hitung frekuensi harapan.")
    event = questions.next_event(db, lesson.id, now_ms=80_000)
    assert event["kind"] == "misconception" and "Frekuensi harapan itu sama saja" in event["text"]


def test_the_misconception_matches_the_topic_being_taught_now():
    profile = profiles.get("matematika-fase-e")
    recent = [
        TranscriptSegment(session_id="s", seq=0, start_ms=0, end_ms=1, text="Dua dadu punya ruang sampel tiga puluh enam."),
        TranscriptSegment(session_id="s", seq=1, start_ms=2, end_ms=3, text="Sekarang uang logam, tiap lemparan saling bebas."),
    ]
    assert questions._misconception(profile, recent)["source_page"] == 258  # coins, not the dice mentioned earlier
    assert questions._misconception(profile, recent[:1])["source_page"] == 249
    assert questions._misconception(profile, [TranscriptSegment(session_id="s", seq=0, start_ms=0, end_ms=1, text="Selamat pagi.")]) is None


def test_a_student_never_guesses_the_teachers_gender(db, lesson, monkeypatch):
    real_llm(monkeypatch, {StudentQuestion: StudentQuestion(text="Yang Bapak sebut tadi itu kenapa bisa begitu, Bu?", refers_to_line=1)})
    speak(db, lesson, 0, 0, 80_000)
    assert questions.next_event(db, lesson.id, now_ms=80_000)["text"] == "Yang Bapak/Ibu sebut tadi itu kenapa bisa begitu?"
    assert questions._tidy("Satu per enam bukan, Pak?") == "Satu per enam bukan?"
    assert questions._tidy("Ibunya mewariskan gen lesung pipi.") == "Ibunya mewariskan gen lesung pipi."


def test_every_misconception_in_the_profile_has_its_page_number():
    known = profiles.get("matematika-fase-e")["misconceptions"]
    assert len(known) == 5
    assert all(m["source_page"] and m["triggers"] and m["ask"] and m["misconception"] for m in known)


# --- reacting: the satisfied signal ---


def ask(db, lesson):
    speak(db, lesson, 0, 0, 80_000)
    return questions.next_event(db, lesson.id, now_ms=80_000)


def test_the_student_waits_for_an_answer_then_shows_it_landed(db, lesson):
    asked = ask(db, lesson)
    assert questions.next_event(db, lesson.id, now_ms=85_000) is None  # the teacher has not answered yet
    speak(db, lesson, 1, 86_000, 90_000)
    assert questions.next_event(db, lesson.id, now_ms=90_000) is None  # 4 s of answer: still listening
    assert db.get(Question, asked["id"]).answered_at_ms == 86_000
    speak(db, lesson, 2, 91_000, 96_000)
    reaction = questions.next_event(db, lesson.id, now_ms=96_000)
    assert reaction["kind"] == "reaction" and reaction["satisfied"] is True
    assert reaction["question_id"] == asked["id"] and reaction["persona"] == asked["persona"]
    assert questions.next_event(db, lesson.id, now_ms=97_000) is None  # settled: the teacher carries on


def test_an_unsettled_answer_gets_one_follow_up_and_then_always_settles(db, lesson, monkeypatch):
    asked = ask(db, lesson)
    real_llm(monkeypatch, {StudentReaction: StudentReaction(satisfied=False, text="Maaf, bagian tadi saya belum paham. Boleh diulang?")})
    speak(db, lesson, 1, 81_000, 91_000)
    follow_up = questions.next_event(db, lesson.id, now_ms=91_000)
    assert follow_up["satisfied"] is False and follow_up["question_id"] == asked["id"]

    speak(db, lesson, 2, 92_000, 102_000)
    settled = questions.next_event(db, lesson.id, now_ms=102_000)
    assert settled["satisfied"] is True and settled["question_id"] == follow_up["id"]
    assert kinds(db) == ["regular", "reaction", "reaction"]  # never a second follow-up


def test_a_failing_provider_never_leaves_the_teacher_stuck(db, lesson, monkeypatch):
    ask(db, lesson)
    real_llm(monkeypatch, {StudentReaction: llm.LLMError("503")})
    speak(db, lesson, 1, 81_000, 91_000)
    reaction = questions.next_event(db, lesson.id, now_ms=91_000)
    assert reaction["satisfied"] is True and reaction["text"] == questions.CANNED_SATISFIED


def test_no_new_question_while_one_is_open(db, lesson):
    ask(db, lesson)
    speak(db, lesson, 1, 81_000, 86_000)  # 5 s of answer so far
    assert questions.next_event(db, lesson.id, now_ms=86_000) is None
    assert kinds(db) == ["regular"]


# --- answering the teacher's question ---


def test_a_student_answers_when_the_teacher_ends_on_a_question(db, lesson, monkeypatch):
    prompts = real_llm(monkeypatch, {StudentAnswer: StudentAnswer(is_question=True, text="Mungkin karena ada enam sisi?")})
    speak(db, lesson, 0, 0, 10_000, "Dadu punya enam sisi. Ada yang tahu berapa peluang muncul angka satu?")
    event = questions.next_event(db, lesson.id, now_ms=10_000)
    assert (event["kind"], event["text"], event["refers_to_ms"]) == ("answer", "Mungkin karena ada enam sisi?", 0)
    assert "Ada yang tahu berapa peluang muncul angka satu?" in prompts[0]

    speak(db, lesson, 1, 14_000, 20_000, "Betul. Menurut kalian kenapa begitu?")
    assert questions.next_event(db, lesson.id, now_ms=20_000) is None  # at most one answer per 45 s


def test_a_rhetorical_question_gets_no_answer(db, lesson, monkeypatch):
    real_llm(monkeypatch, {StudentAnswer: StudentAnswer(is_question=False, text="")})
    speak(db, lesson, 0, 0, 10_000, "Jadi hasilnya enam, paham ya?")
    assert questions.next_event(db, lesson.id, now_ms=10_000) is None
    assert kinds(db) == []


def test_a_statement_is_not_answered_and_a_failed_provider_stays_silent(db, lesson, monkeypatch):
    real_llm(monkeypatch, {StudentAnswer: llm.LLMError("503")})
    speak(db, lesson, 0, 0, 10_000, "Dadu punya enam sisi.")
    assert questions.next_event(db, lesson.id, now_ms=10_000) is None
    speak(db, lesson, 1, 11_000, 20_000, "Ada yang tahu berapa peluangnya?")
    assert questions.next_event(db, lesson.id, now_ms=20_000) is None  # better silent than a made-up answer


def test_questions_are_recognised_without_a_question_mark():
    assert metrics.closing_question("Dadu punya enam sisi. Berapa peluang muncul angka satu") == "Berapa peluang muncul angka satu"
    assert metrics.closing_question("Menurut kalian mana yang lebih besar peluangnya.")
    assert metrics.closing_question("Apakah hasilnya selalu sama") and metrics.closing_question("Gimana caranya")
    assert metrics.closing_question("Langkah pertama kita tulis ruang sampelnya.") is None  # "langkah" is not a question
    assert metrics.closing_question("Ada yang tahu? Baik, kita lanjutkan.") is None  # the piece does not end on it


# --- nudge and capstone ---


def test_one_nudge_per_silence(db, lesson):
    speak(db, lesson, 0, 0, 10_000)
    assert questions.next_event(db, lesson.id, now_ms=45_000)["kind"] == "nudge"
    assert questions.next_event(db, lesson.id, now_ms=80_000) is None
    speak(db, lesson, 1, 81_000, 90_000)
    assert questions.next_event(db, lesson.id, now_ms=90_000) is None


def test_capstone_is_stored_and_ends_the_questions(db, lesson):
    speak(db, lesson, 0, 0, 10_000)
    event = questions.capstone(db, lesson.id)
    assert event["kind"] == "capstone" and event["asked_at_ms"] == 10_000 and event["text"] == questions.CANNED_CAPSTONE
    assert db.exec(select(Question).where(Question.kind == "capstone")).one().id == event["id"]
    speak(db, lesson, 1, 11_000, 120_000)
    assert questions.next_event(db, lesson.id, now_ms=120_000) is None
    assert db.get(Question, event["id"]).answered_at_ms == 11_000  # the answer is still timed


def test_capstone_wording_comes_from_the_llm(db, lesson, monkeypatch):
    real_llm(monkeypatch, {StudentQuestion: StudentQuestion(text="Jadi kapan peluang boleh dijumlahkan?", refers_to_line=1, level=2)})
    speak(db, lesson, 0, 0, 10_000)
    event = questions.capstone(db, lesson.id)
    assert (event["text"], event["level"], event["refers_to_ms"]) == ("Jadi kapan peluang boleh dijumlahkan?", 2, 0)
