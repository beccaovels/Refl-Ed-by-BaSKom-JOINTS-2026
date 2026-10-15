"""Computed metrics and the evidence check: fixed timestamps in, exact numbers out."""

import pymupdf

from app.models import Material, Question, SlideEvent, TranscriptSegment
from app.services import evidence, metrics, rag

SLIDE = (
    "Fungsi kuadrat adalah fungsi polinomial berderajat dua dengan bentuk umum "
    "a x kuadrat ditambah b x ditambah c dan nilai a tidak sama dengan nol"
)


def say(db, lesson, seq, start_ms, end_ms, text):
    db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start_ms, end_ms=end_ms, text=text))
    db.commit()


def segment(start_ms, text):
    return TranscriptSegment(session_id="s", seq=0, start_ms=start_ms, end_ms=start_ms + 5_000, text=text)


# --- metrics ---


def test_pace_counts_speaking_time_only():
    # 20 words in 10 s of speech is 120 words per minute, however long the silence between.
    spoken = [(0, 5_000, "satu dua tiga empat lima enam tujuh delapan sembilan sepuluh")] * 2
    assert metrics.pace(spoken) == 120
    assert metrics.pace([]) == 0


def test_pauses_and_wait_time_after_a_question():
    spoken = [
        (0, 5_000, "Bentuknya parabola."),
        (5_500, 9_000, "Ada yang tahu kenapa melengkung?"),  # 0.5 s gap before: not a pause
        (13_000, 18_000, "Betul, karena pangkatnya dua."),  # 4 s after a question: thinking time
        (20_500, 25_000, "Sekarang kita lanjut."),  # 2.5 s gap: a pause, but not after a question
    ]
    assert metrics.pauses(spoken) == 2
    assert metrics.wait_times(spoken) == [4_000]
    assert metrics.thinking_time_share([4_000, 1_000]) == 0.5
    assert metrics.thinking_time_share([]) is None


def test_teacher_questions_with_and_without_a_question_mark():
    assert len(metrics.teacher_questions("Ini parabola. Kenapa bentuknya begitu? Coba pikirkan.")) == 1
    assert len(metrics.teacher_questions("Ada yang tahu nilai a di sini")) == 1
    assert metrics.teacher_questions("Nilai a tidak boleh nol.") == []


def test_time_per_slide_adds_up_return_visits():
    turns = [(1, 0), (2, 60_000), (1, 90_000)]
    assert metrics.time_per_slide(turns, end_ms=120_000) == [{"page": 1, "ms": 90_000}, {"page": 2, "ms": 30_000}]
    assert metrics.time_per_slide([], end_ms=120_000) == []


def test_reading_the_slide_scores_high_and_own_words_score_low():
    read_out = "Fungsi kuadrat adalah fungsi polinomial berderajat dua dengan bentuk umum a x kuadrat ditambah b x ditambah c"
    own_words = "Coba bayangkan kalian melempar bola basket ke ring, lintasannya naik lalu turun seperti lengkungan"
    assert metrics.reading_share([(read_out, SLIDE)]) >= 0.9
    assert metrics.reading_share([(own_words, SLIDE)]) == 0
    assert metrics.reading_share([]) is None


def test_a_short_phrase_from_the_slide_is_not_reading():
    # Six shared words in a row is a term or a definition, not reading the slide out.
    said = "Jadi ingat ya, fungsi kuadrat adalah fungsi polinomial berderajat, itu intinya anak-anak"
    assert metrics.reading_share([(said, SLIDE)]) == 0


def test_compute_reads_a_whole_session(db, lesson, tmp_path):
    path = tmp_path / "bab.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_textbox((50, 50, 550, 300), SLIDE)
    pdf.save(path)
    material = Material(user_id=lesson.user_id, filename="bab.pdf", path=str(path), page_count=1)
    db.add(material)
    db.commit()
    rag.index_material(db, material.id)
    lesson.material_id = material.id
    db.add(lesson)
    db.add(SlideEvent(session_id=lesson.id, page=1, t_ms=0))
    db.add(Question(session_id=lesson.id, kind="regular", text="Kenapa?", asked_at_ms=10_000, answered_at_ms=12_500))
    db.add(Question(session_id=lesson.id, kind="nudge", text="Silakan lanjut.", asked_at_ms=50_000))
    db.commit()
    say(db, lesson, 0, 0, 10_000, "Eee, coba bayangkan bola dilempar ke atas, lintasannya melengkung. Ada yang tahu kenapa?")
    say(db, lesson, 1, 14_000, 24_000, SLIDE)

    result = metrics.compute(db, lesson.id)
    public = result.public()

    assert set(public) == {
        "words_per_minute", "pause_count", "questions_asked", "wait_time_avg_ms", "reading_share",
        "response_time_avg_ms", "filler_count", "time_per_slide",
    }  # fmt: skip
    assert public["pause_count"] == 1
    assert public["questions_asked"] == 1
    assert public["wait_time_avg_ms"] == 4_000
    assert public["response_time_avg_ms"] == 2_500  # the nudge is not a question to answer
    assert public["filler_count"] == 1
    assert public["time_per_slide"] == [{"page": 1, "ms": 24_000}]
    assert 0.5 < public["reading_share"] < 1  # the second piece was read, the first was not


def test_a_shared_screen_is_not_a_slide_and_its_speech_is_not_counted_as_reading(db, lesson, tmp_path):
    path = tmp_path / "bab.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_textbox((50, 50, 550, 300), SLIDE)
    pdf.save(path)
    material = Material(user_id=lesson.user_id, filename="bab.pdf", path=str(path), page_count=1)
    db.add(material)
    db.commit()
    rag.index_material(db, material.id)
    lesson.material_id = material.id
    db.add(lesson)
    # PDF for 60 s, a shared screen for 120 s (page 0), then the PDF again
    for t_ms, page in ((0, 1), (60_000, 0), (180_000, 1)):
        db.add(SlideEvent(session_id=lesson.id, page=page, t_ms=t_ms))
    db.commit()
    say(db, lesson, 0, 0, 20_000, SLIDE)  # read aloud from the slide
    say(db, lesson, 1, 70_000, 90_000, "sekarang lihat contoh yang saya siapkan sendiri tentang pelemparan koin dan dadu di layar")
    say(db, lesson, 2, 200_000, 220_000, "kita kembali ke bahan tadi dan saya jelaskan dengan kata-kata saya sendiri saja")

    result = metrics.compute(db, lesson.id)

    assert result.time_per_slide == [{"page": 1, "ms": 100_000}]  # page 0 is not listed as a slide
    assert result.shared_ms == 120_000
    assert result.public()["time_per_slide"] == [{"page": 1, "ms": 100_000}]
    # only the two pieces said beside the slide count: one read, one in the teacher's own words
    assert 0.4 < result.reading_share < 0.8


def test_a_lesson_spent_sharing_a_screen_has_no_reading_share(db, lesson, tmp_path):
    path = tmp_path / "bab.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_textbox((50, 50, 550, 300), SLIDE)
    pdf.save(path)
    material = Material(user_id=lesson.user_id, filename="bab.pdf", path=str(path), page_count=1)
    db.add(material)
    db.commit()
    rag.index_material(db, material.id)
    lesson.material_id = material.id
    db.add(lesson)
    db.add(SlideEvent(session_id=lesson.id, page=0, t_ms=0))
    db.commit()
    say(db, lesson, 0, 5_000, 25_000, SLIDE)  # the same words, but no slide is on show to read them from

    result = metrics.compute(db, lesson.id)

    assert result.reading_share is None and result.time_per_slide == [] and result.shared_ms == 25_000


def test_no_material_means_no_reading_share(db, lesson):
    say(db, lesson, 0, 0, 10_000, "Hari ini kita belajar fungsi kuadrat.")
    public = metrics.compute(db, lesson.id).public()
    assert public["reading_share"] is None
    assert public["response_time_avg_ms"] is None
    assert public["time_per_slide"] == []


# --- evidence ---


def test_a_real_quote_is_found_despite_case_and_punctuation():
    segments = [segment(0, "Selamat pagi anak-anak."), segment(135_000, "Coba bayangkan bola yang dilempar ke atas, lintasannya melengkung.")]
    assert evidence.find_quote("coba bayangkan bola yang dilempar ke atas", segments) == 135_000


def test_a_fabricated_quote_is_not_found():
    segments = [segment(0, "Coba bayangkan bola yang dilempar ke atas.")]
    assert evidence.find_quote("coba bayangkan roket yang diluncurkan ke bulan", segments) is None
    assert evidence.find_quote("ke atas", segments) is None  # too short to prove anything
    assert evidence.find_quote(None, segments) is None


def test_a_quote_may_run_across_two_audio_pieces():
    segments = [segment(0, "Rumus sumbu simetrinya adalah"), segment(6_000, "x sama dengan negatif b per dua a.")]
    assert evidence.find_quote("sumbu simetrinya adalah x sama dengan negatif b", segments) == 0


def test_banned_words_are_caught_but_maths_phrases_are_not():
    assert evidence.banned_words("Penjelasan Anda kurang jelas dan seharusnya lebih pelan.") == ["kurang", "seharusnya"]
    assert evidence.banned_words("You should slow down.") == ["should"]
    assert evidence.banned_words("Nilai x kurang dari tiga, lalu dikurangi dua, kurang lebih begitu.") == []
    assert evidence.banned_words("Anda bisa mencoba membuka dengan sebuah cerita.") == []
