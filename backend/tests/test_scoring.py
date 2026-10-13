"""The report: shape, the evidence check, the feedback rules and the score arithmetic."""

import pytest

from app.core.config import settings
from app.models import Question, TranscriptSegment, User
from app.services import evidence, llm, questions, scoring
from app.services.report_schema import ReportOut
from app.services.rubric import CARDS, band, growth_label
from app.services.scoring import Assessment, Feedback, IdeaDraft, Rating

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
