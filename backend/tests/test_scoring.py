"""The report: shape, the evidence check, the feedback rules and the score arithmetic."""

import pytest

from app.core.config import settings
from app.models import Material, Question, SlideEvent, TranscriptSegment, User
from app.services import evidence, examples, llm, questions, scoring
from app.services.metrics import LessonMetrics
from app.services.report_schema import ReportOut
from app.services.rubric import CARDS, band, growth_label
from app.services.scoring import Assessment, ExampleFeedback, Feedback, IdeaDraft, Rating

LESSON = [
    "Selamat pagi anak-anak, hari ini kita belajar fungsi kuadrat dan grafiknya.",
    "Coba bayangkan kalian melempar bola basket ke ring, lintasannya melengkung naik lalu turun.",
    "Lengkungan seperti itu dalam matematika kita sebut parabola. Ada yang tahu kenapa bentuknya begitu?",
    "Bentuk umumnya adalah a x kuadrat ditambah b x ditambah c, dan nilai a tidak boleh nol.",
    "Kalau a positif parabolanya terbuka ke atas, kalau a negatif terbuka ke bawah.",
    "Jadi hari ini kita sudah belajar bentuk umum dan arah parabola.",
]
REAL_QUOTE = "coba bayangkan kalian melempar bola basket ke ring"
FAKE_QUOTE = "mari kita lihat roket yang diluncurkan ke bulan"


@pytest.fixture
def taught(db, lesson):
    """A lesson with enough speech to be read: six pieces, 10 s each, 4 s apart."""
    for seq, text in enumerate(LESSON):
        start = seq * 14_000
        db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start, end_ms=start + 10_000, text=text))
    db.commit()
    return lesson


def real_llm(monkeypatch, assessment):
    """Pretend a provider is configured and answers with `assessment`."""
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    prompts = []

    def generate(prompt, schema, **kwargs):
        prompts.append(prompt)
        return assessment

    monkeypatch.setattr(llm, "generate_json", generate)
    return prompts


def rate_all(level, quote=REAL_QUOTE):
    keys = [p.key for card in CARDS for p in card.parameters if p.source == "llm"]
    return [Rating(key=key, level=level, quote=quote) for key in keys]


def by_key(report):
    return {d["key"]: d for d in report["dimensions"]}


# --- shape ---


def test_sample_report_has_the_contract_shape(db, taught):
    questions.capstone(db, taught.id)
    report = scoring.build_report(db, taught.id)

    assert set(report) == set(ReportOut.model_fields)
    assert [d["key"] for d in report["dimensions"]] == [
        "content_accuracy", "teaching_flow", "clarity", "engagement", "pacing", "delivery",
    ]  # fmt: skip
    assert report["profile"] == {"id": "matematika-fase-e", "label": "Matematika Kelas X"}
    assert 0 <= report["overall"]["score"] <= 100
    assert report["overall"]["label_text"] in ("Mulai tumbuh", "Berkembang", "Kuat")
    assert len(report["questions"]) == 1


def test_feedback_rules_hold(db, taught):
    report = scoring.build_report(db, taught.id)

    assert report["strengths"] and all(item["kind"] == "worked" for item in report["strengths"])
    assert report["strengths"][0]["quote"]  # opens with the teacher's own words
    assert len(report["ideas"]) <= 3
    assert evidence.banned_words(str(report)) == []
    for dimension in report["dimensions"]:
        kinds = [item["kind"] for item in dimension["items"]]
        assert len(kinds) <= 2 and kinds == sorted(kinds, reverse=True)  # the strength comes first


def test_free_tier_locks_pacing_and_delivery(db, taught):
    cards = by_key(scoring.build_report(db, taught.id))
    assert cards["pacing"]["locked"] and cards["pacing"]["score"] is None and cards["pacing"]["parameters"] == []
    assert cards["delivery"]["locked"]
    assert not cards["clarity"]["locked"] and cards["clarity"]["score"] is not None


def test_institutional_tier_sees_pacing(db, taught):
    user = db.get(User, taught.user_id)
    user.tier = "institutional"
    db.add(user)
    db.commit()
    cards = by_key(scoring.build_report(db, taught.id))
    assert cards["pacing"]["score"] is not None
    assert {p["key"] for p in cards["pacing"]["parameters"] if p["available"]} >= {"speaking_rate", "pauses"}
    # No signal bins yet: the card says so and does not count against the teacher.
    assert not cards["delivery"]["available"] and cards["delivery"]["unavailable_reason"]


def test_a_very_short_recording_is_not_scored(db, lesson, monkeypatch):
    def never(*args, **kwargs):
        raise AssertionError("the LLM must not be called for a recording this short")

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(llm, "generate_json", never)
    db.add(TranscriptSegment(session_id=lesson.id, seq=0, start_ms=0, end_ms=4_000, text="Selamat pagi anak-anak."))
    db.commit()

    report = scoring.build_report(db, lesson.id)
    assert report["overall"]["score"] is None
    assert report["strengths"]  # still opens with something kind and true
    assert all(d["score"] is None for d in report["dimensions"])


# --- evidence ---


def test_a_fabricated_quote_is_dropped_and_a_real_one_gets_its_timestamp(db, taught, monkeypatch):
    real_llm(
        monkeypatch,
        Assessment(
            ratings=rate_all(3),
            feedback=[
                Feedback(dimension="clarity", kind="worked", text="Pada 00:14 Anda memakai contoh bola.", quote=REAL_QUOTE),
                Feedback(dimension="clarity", kind="noticed", text="Pada 03:00 ada cerita roket.", quote=FAKE_QUOTE),
            ],
            summary="Contoh bola basket Anda langsung terasa dekat bagi murid.",
            ideas=[],
        ),
    )
    items = by_key(scoring.build_report(db, taught.id))["clarity"]["items"]
    assert [(item["kind"], item["t_ms"]) for item in items] == [("worked", 14_000)]


def test_a_high_level_without_a_real_quote_is_lowered(db, taught, monkeypatch):
    real_llm(monkeypatch, Assessment(ratings=rate_all(5, quote=FAKE_QUOTE), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    clarity = by_key(scoring.build_report(db, taught.id))["clarity"]
    assert clarity["score"] == 60  # every 5 fell to 3: three fifths of the points

    real_llm(monkeypatch, Assessment(ratings=rate_all(5, quote=REAL_QUOTE), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    assert by_key(scoring.build_report(db, taught.id))["clarity"]["score"] == 100


# --- wording ---


def test_banned_wording_never_reaches_the_teacher(db, taught, monkeypatch):
    real_llm(
        monkeypatch,
        Assessment(
            ratings=rate_all(3),
            feedback=[Feedback(dimension="clarity", kind="noticed", text="Penjelasan Anda kurang jelas.", quote=REAL_QUOTE)],
            summary="Anda seharusnya berbicara lebih pelan.",
            ideas=[
                IdeaDraft(text="Anda should membuka dengan cerita.", ready_to_use="Pernahkah kalian melihat air mancur?"),
                IdeaDraft(text="Satu ide: buka dengan pertanyaan.", ready_to_use="Pernahkah kalian melihat air mancur?"),
            ],
        ),
    )
    report = scoring.build_report(db, taught.id)
    assert evidence.banned_words(str(report)) == []
    assert [idea["text"] for idea in report["ideas"]] == ["Satu ide: buka dengan pertanyaan."]
    assert report["tip"] == "Satu ide: buka dengan pertanyaan."
    assert report["overall"]["summary"] == report["strengths"][0]["text"]


def test_emotion_labels_never_reach_the_teacher(db, taught, monkeypatch):
    real_llm(
        monkeypatch,
        Assessment(
            ratings=rate_all(3),
            feedback=[
                Feedback(dimension="clarity", kind="noticed", text="Pada 00:14 Anda terdengar gugup.", quote=REAL_QUOTE),
                Feedback(dimension="engagement", kind="worked", text="Pada 00:14 contoh bola membuat konsepnya konkret.", quote=REAL_QUOTE),
            ],
            summary="Anda tampak percaya diri hari ini.",
            ideas=[],
        ),
    )
    report = scoring.build_report(db, taught.id)
    assert evidence.emotion_words(str(report)) == []
    assert by_key(report)["clarity"]["items"] == []
    assert evidence.emotion_words("Tegangan listrik itu seperti tekanan air.") == []  # a physics word, not a mood


def test_at_most_three_ideas(db, taught, monkeypatch):
    ideas = [IdeaDraft(text=f"Satu ide: nomor {n}.", ready_to_use="Coba tanyakan ini kepada murid.") for n in range(5)]
    real_llm(monkeypatch, Assessment(ratings=rate_all(3), feedback=[], summary="Terima kasih sudah berlatih.", ideas=ideas))
    assert len(scoring.build_report(db, taught.id)["ideas"]) == 3


# --- arithmetic ---


def test_levels_become_points_and_missing_parameters_share_their_weight(db, taught, monkeypatch):
    real_llm(monkeypatch, Assessment(ratings=rate_all(4), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    cards = by_key(scoring.build_report(db, taught.id))

    assert cards["teaching_flow"]["score"] == 80  # level 4 of 5 on every parameter
    flow = {p["key"]: p for p in cards["teaching_flow"]["parameters"]}
    assert flow["builds_up"]["score"] == 24 and flow["builds_up"]["max"] == 30

    engagement = {p["key"]: p for p in cards["engagement"]["parameters"]}
    assert not engagement["own_words"]["available"]  # no PDF was uploaded
    assert not engagement["builds_on_questions"]["available"]  # no student question was answered
    assert engagement["invites_students"]["available"] and engagement["invites_students"]["source"] == "computed"
    measured = [p for p in engagement.values() if p["available"]]
    assert cards["engagement"]["score"] == round(sum(p["score"] for p in measured) / sum(p["max"] for p in measured) * 100)


def test_overall_is_the_weighted_mean_of_the_cards_shown(db, taught, monkeypatch):
    real_llm(monkeypatch, Assessment(ratings=rate_all(4), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    report = scoring.build_report(db, taught.id)
    shown = [d for d in report["dimensions"] if d["score"] is not None]
    assert {d["key"] for d in shown} == {"content_accuracy", "teaching_flow", "clarity", "engagement"}
    expected = round(sum(d["score"] * d["weight"] for d in shown) / sum(d["weight"] for d in shown))
    assert report["overall"]["score"] == expected
    assert sum(card.weight for card in CARDS) == 100
    assert all(sum(p.max for p in card.parameters) == 100 for card in CARDS)


def test_target_bands_reward_the_comfortable_range_not_the_maximum():
    assert band(130, 60, 100, 160, 210) == 1.0  # inside the band: full marks
    assert band(100, 60, 100, 160, 210) == 1.0
    assert band(80, 60, 100, 160, 210) == 0.5
    assert band(260, 60, 100, 160, 210) == 0.0  # far too fast
    assert [growth_label(score) for score in (49, 50, 79, 80)] == ["starting", "developing", "developing", "strong"]


# --- prompt ---


def test_the_prompt_carries_the_profile_the_transcript_and_the_answers(db, taught, monkeypatch):
    db.add(Question(session_id=taught.id, kind="regular", text="Kenapa a tidak boleh nol?", asked_at_ms=52_000, answered_at_ms=56_000))
    db.commit()
    prompts = real_llm(monkeypatch, Assessment(ratings=rate_all(3), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    report = scoring.build_report(db, taught.id)

    prompt = prompts[0]
    assert "Menjelaskan alasan di balik rumus" in prompt  # the maths profile's own Clarity parameter
    assert "[00:14] Coba bayangkan kalian melempar bola basket" in prompt
    assert "Murid bertanya: Kenapa a tidak boleh nol?" in prompt and "`answers_correct`" in prompt
    assert "literasi finansial" in prompt  # context seeds for the ideas
    asked = report["questions"][0]
    assert asked["response_time_ms"] == 4_000 and asked["answer_quote"].startswith("Kalau a positif")
    titles = {p["title"] for p in by_key(report)["clarity"]["parameters"]}
    assert "Menjelaskan alasan di balik rumus" in titles


def test_the_report_lists_every_exchange_with_a_student(db, taught, monkeypatch):
    asked = Question(session_id=taught.id, kind="regular", text="Kenapa a tidak boleh nol?", asked_at_ms=52_000, answered_at_ms=56_000, level=2)
    db.add(asked)
    db.commit()
    db.add(Question(session_id=taught.id, kind="reaction", text="Oh, jadi garis lurus.", asked_at_ms=66_000, reply_to=asked.id, satisfied=True))
    # The third piece of the lesson ends on "Ada yang tahu kenapa bentuknya begitu?"; Sari answered it.
    db.add(Question(session_id=taught.id, kind="answer", text="Karena pangkatnya dua?", asked_at_ms=38_500, refers_to_ms=28_000))
    db.add(Question(session_id=taught.id, kind="nudge", text="Silakan lanjut.", asked_at_ms=80_000))
    db.commit()
    prompts = real_llm(monkeypatch, Assessment(ratings=rate_all(3), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))

    exchanges = scoring.build_report(db, taught.id)["questions"]

    assert [e["kind"] for e in exchanges] == ["answer", "regular"]  # in time order; no nudge, no reaction row
    answer, question = exchanges
    assert answer["teacher_question"] == "Ada yang tahu kenapa bentuknya begitu?"
    assert answer["answer_quote"].startswith("Bentuk umumnya adalah")  # how the teacher built on it
    assert (question["level"], question["satisfied"], question["follow_up"]) == (2, True, None)
    assert "Guru bertanya kepada kelas, lalu murid menjawab: Karena pangkatnya dua?" in prompts[0]


# --- the teacher's handwritten worked examples ---

WRITTEN_LINE = "n(S) = 6 × 6 = 36"  # the first step of the sample reading


def example(db, lesson, confirm=True, shown_at=14_000):
    """A photo of the teacher's working in the lesson's material, read by the sample reader."""
    if not lesson.material_id:
        holder = Material(user_id=lesson.user_id)
        db.add(holder)
        db.commit()
        lesson.material_id = holder.id
        db.add(lesson)
        db.commit()
    row = examples.read(db, examples.add(db, lesson.material_id, "contoh.jpg", "contoh.jpg").id)
    if confirm:
        row = examples.confirm(db, row.id)
    if shown_at is not None:
        db.add(SlideEvent(session_id=lesson.id, page=row.page, t_ms=shown_at))
        db.commit()
    return row


def parameters(report, card):
    return {p["key"]: p for p in by_key(report)[card]["parameters"]}


def test_without_a_worked_example_the_cards_score_exactly_as_before(db, taught, monkeypatch):
    ratings = [Rating(key="material_agreement", level=5, quote=REAL_QUOTE), Rating(key="correct_terms", level=3)]
    ratings += [Rating(key=key, level=level) for key, level in (("profile_a", 2), ("terms_explained", 3), ("step_by_step", 1), ("profile_b", 3))]
    real_llm(monkeypatch, Assessment(ratings=ratings, feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    report = scoring.build_report(db, taught.id)

    assert report["examples"] == []
    assert not parameters(report, "content_accuracy")["worked_example"]["available"]
    assert not parameters(report, "clarity")["worked_steps"]["available"]
    assert by_key(report)["content_accuracy"]["score"] == 85  # (50 x 5/5 + 30 x 3/5) of 80, as with the old points
    assert by_key(report)["clarity"]["score"] == 44  # (30 x 2 + 25 x 3 + 25 x 1 + 20 x 3) / 5, as with the old points


def test_an_example_counts_only_when_confirmed_and_shown(db, taught, monkeypatch):
    unconfirmed = example(db, taught, confirm=False)
    never_shown = example(db, taught, shown_at=None)
    prompts = real_llm(monkeypatch, Assessment(ratings=rate_all(4), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    report = scoring.build_report(db, taught.id)

    assert not parameters(report, "content_accuracy")["worked_example"]["available"]
    assert not parameters(report, "clarity")["worked_steps"]["available"]
    assert "(guru tidak menampilkan contoh soal tulisan tangan)" in prompts[0]
    assert "- `worked_steps` (" not in prompts[0] and "- `worked_example` (" not in prompts[0]  # not asked to rate them
    first, second = report["examples"]  # both are still listed, so the teacher can confirm later
    assert (first["example_id"], first["confirmed"], first["check"], first["shown_at_ms"]) == (unconfirmed.id, False, None, 14_000)
    assert (second["example_id"], second["confirmed"], second["shown_at_ms"]) == (never_shown.id, True, None)
    assert first["reading"]["question"].startswith("(Contoh)")


def test_a_confirmed_example_that_was_shown_is_rated(db, taught, monkeypatch):
    shown = example(db, taught)
    prompts = real_llm(monkeypatch, Assessment(ratings=rate_all(4), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[]))
    report = scoring.build_report(db, taught.id)

    prompt = prompts[0]
    assert f"[Halaman {shown.page}, ditampilkan sejak 00:14]" in prompt and f"1. {WRITTEN_LINE}" in prompt
    assert "Catatan pemeriksaan: langkah dan jawaban akhir sejalan dengan hitungan kami." in prompt
    assert "- `worked_example` (Contoh soal dikerjakan dengan tepat)" in prompt
    assert "- `worked_steps` (Langkah pengerjaan tertata dan dijelaskan)" in prompt
    assert "diagram ruang sampel" in prompt  # the maths profile's own practice list
    assert "Contoh soal yang ditulis tangan oleh guru" not in prompt.split("## Contoh soal")[0]  # not also given as reference material
    worked = parameters(report, "content_accuracy")["worked_example"]
    assert (worked["available"], worked["score"], worked["max"]) == (True, 16, 20)
    assert parameters(report, "clarity")["worked_steps"]["score"] == 16
    assert report["examples"][0]["check"]["answer"] == "follows"


def test_a_written_line_is_the_teachers_own_words_once_confirmed(db, taught, monkeypatch):
    shown = example(db, taught)
    assessment = Assessment(
        ratings=[Rating(key="worked_steps", level=5, quote=WRITTEN_LINE)],
        feedback=[Feedback(dimension="clarity", kind="worked", text="Pada tulisan Anda, ruang sampel dihitung lebih dulu.", quote=WRITTEN_LINE)],
        summary="Terima kasih sudah berlatih.",
        ideas=[],
    )
    real_llm(monkeypatch, assessment)
    report = scoring.build_report(db, taught.id)
    assert parameters(report, "clarity")["worked_steps"]["score"] == 20  # the 5 stands: the quote is in their writing
    (item,) = by_key(report)["clarity"]["items"]
    assert (item["quote"], item["page"], item["t_ms"]) == (WRITTEN_LINE, shown.page, 14_000)

    assert evidence.find_written("n(S) = 6 × 6 = 99", {1: [WRITTEN_LINE]}) is None  # a line they did not write
    assert evidence.find_written("6 × 6", {1: [WRITTEN_LINE]}) is None  # too short to be a quote


def test_a_written_line_from_an_unconfirmed_example_is_not_evidence(db, taught, monkeypatch):
    example(db, taught, confirm=False)
    feedback = [Feedback(dimension="clarity", kind="worked", text="Pada tulisan Anda, ruang sampel dihitung lebih dulu.", quote=WRITTEN_LINE)]
    real_llm(monkeypatch, Assessment(ratings=rate_all(3), feedback=feedback, summary="Terima kasih sudah berlatih.", ideas=[]))
    assert by_key(scoring.build_report(db, taught.id))["clarity"]["items"] == []


def test_the_working_is_not_marked_down_unless_the_check_named_a_step(db, taught, monkeypatch):
    shown = example(db, taught)
    marked_down = Assessment(ratings=[Rating(key="worked_example", level=1)], feedback=[], summary="Terima kasih sudah berlatih.", ideas=[])
    real_llm(monkeypatch, marked_down)
    assert parameters(scoring.build_report(db, taught.id), "content_accuracy")["worked_example"]["score"] == 12  # held at 3

    check = dict(shown.check_result, answer="recheck")
    check["steps"] = [dict(step, status="recheck", note="Tertulis 36, sedangkan hitungan kami 30.") if step["n"] == 1 else step for step in check["steps"]]
    shown.check_result = check
    db.add(shown)
    db.commit()
    prompts = real_llm(monkeypatch, marked_down)
    assert parameters(scoring.build_report(db, taught.id), "content_accuracy")["worked_example"]["score"] == 4
    assert "Catatan pemeriksaan: langkah 1: Tertulis 36, sedangkan hitungan kami 30.; jawaban akhir berbeda" in prompts[0]


def test_each_example_gets_at_most_one_worked_and_one_noticed(db, taught, monkeypatch):
    shown = example(db, taught)
    about = [
        # The model is shown "3. P(A) = ..." and often quotes the number too; the line is still the teacher's.
        ExampleFeedback(page=shown.page, kind="noticed", text="Rumus peluang belum tertulis sebelum angkanya dimasukkan.", quote="3. P(A) = n(A) / n(S) = 6/36"),
        ExampleFeedback(page=shown.page, kind="worked", text="Pada 00:14 Anda mengaitkannya dengan lemparan bola.", quote=REAL_QUOTE),
        ExampleFeedback(page=shown.page, kind="worked", text="Butir kedua yang sejenis tidak dipakai.", quote=WRITTEN_LINE),
        ExampleFeedback(page=shown.page, kind="noticed", text="Tulisan Anda kurang lengkap.", quote=WRITTEN_LINE),
        ExampleFeedback(page=shown.page, kind="noticed", text="Ada baris tentang roket.", quote=FAKE_QUOTE),
        ExampleFeedback(page=99, kind="worked", text="Halaman ini tidak ada.", quote=WRITTEN_LINE),
    ]
    real_llm(monkeypatch, Assessment(ratings=rate_all(3), feedback=[], summary="Terima kasih sudah berlatih.", ideas=[], example_feedback=about))
    worked, noticed = scoring.build_report(db, taught.id)["examples"][0]["items"]  # the strength first
    assert (worked["kind"], worked["t_ms"], worked["page"]) == ("worked", 14_000, None)  # said aloud: when they said it
    assert (noticed["kind"], noticed["t_ms"], noticed["page"]) == ("noticed", 14_000, shown.page)  # written: when it was shown
    assert noticed["text"].startswith("Rumus peluang") and noticed["quote"] == "P(A) = n(A) / n(S) = 6/36"


def test_sample_report_shows_feedback_beside_the_example(db, taught):
    shown = example(db, taught)
    report = scoring.build_report(db, taught.id)
    (item,) = report["examples"][0]["items"]
    assert item["text"].startswith("(Contoh)") and (item["quote"], item["page"]) == (WRITTEN_LINE, shown.page)
    assert parameters(report, "clarity")["worked_steps"]["available"]


def test_time_on_a_worked_example_is_left_out_of_how_time_is_spread_over_slides():
    numbers = LessonMetrics(
        duration_ms=240_000, words=400, words_per_minute=120,
        time_per_slide=[{"page": 1, "ms": 20_000}, {"page": 2, "ms": 20_000}, {"page": 3, "ms": 200_000}],
    )  # fmt: skip
    assert scoring._computed(numbers, own_pages={3})["slide_balance"] == 1.0  # the two slides share their time evenly
    assert scoring._computed(numbers)["slide_balance"] < 0.5  # as an ordinary slide, page 3 would dominate


def test_time_on_a_shared_screen_does_not_change_how_time_is_spread_over_slides():
    slides = [{"page": 1, "ms": 80_000}, {"page": 2, "ms": 40_000}]
    only_slides = LessonMetrics(duration_ms=120_000, words=500, words_per_minute=120, time_per_slide=slides)
    with_sharing = LessonMetrics(duration_ms=360_000, words=500, words_per_minute=120, time_per_slide=slides, shared_ms=240_000)
    balance = scoring._computed(only_slides)["slide_balance"]
    assert balance < 1.0  # slide 1 took two thirds of the slide time
    assert scoring._computed(with_sharing)["slide_balance"] == balance  # four minutes of sharing change nothing


def test_a_report_for_a_lesson_with_a_shared_screen_lists_no_page_zero(db, taught):
    db.add(SlideEvent(session_id=taught.id, page=1, t_ms=0))
    db.add(SlideEvent(session_id=taught.id, page=0, t_ms=30_000))
    db.add(SlideEvent(session_id=taught.id, page=1, t_ms=90_000))
    db.commit()
    report = scoring.build_report(db, taught.id)
    assert all(slide["page"] != 0 for slide in report["metrics"]["time_per_slide"])
