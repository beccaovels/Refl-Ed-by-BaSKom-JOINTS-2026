"""Tone & expression from signal bins: lively versus flat, moments over duration, and what is never scored."""

from app.models import Question, SignalBin, TranscriptSegment, User
from app.services import delivery, evidence, scoring

FLAT_PITCH, LIVELY_PITCH = 0.8, 3.5  # semitones of spread within a bin
STILL_FACE, LIVELY_FACE = 0.02, 0.30


def voice_bin(n, pitch=FLAT_PITCH, volume=0.3):
    return SignalBin(session_id="s", t_start_ms=n * 10_000, pitch_variation=pitch, volume=volume)


def camera_bin(n, pitch=FLAT_PITCH, face=STILL_FACE, hands=0.0, posture=1.0, visible=1.0, measured=True, volume=0.3):
    return SignalBin(
        session_id="s", t_start_ms=n * 10_000, pitch_variation=pitch, volume=volume, expressiveness=face,
        gesture_rate=hands, posture_ok_pct=posture, face_visible_pct=visible, facing_pct=1.0, measured=measured,
    )  # fmt: skip


def said(start_ms, text):
    return TranscriptSegment(session_id="s", seq=start_ms, start_ms=start_ms, end_ms=start_ms + 8_000, text=text)


LESSON = [
    said(0, "Selamat pagi anak-anak, hari ini kita belajar peluang."),
    said(20_000, "Dadu punya enam sisi."),
    said(40_000, "Ada yang tahu berapa peluang muncul angka satu?"),
    said(70_000, "Jadi peluangnya satu per enam."),
]
ASKED = [Question(session_id="s", kind="regular", text="Kenapa satu per enam?", asked_at_ms=58_000, answered_at_ms=61_000)]


def test_a_lively_voice_scores_above_a_flat_one():
    flat, _ = delivery.score([voice_bin(n) for n in range(8)], ASKED, LESSON)
    lively, _ = delivery.score([voice_bin(n, pitch=LIVELY_PITCH) for n in range(8)], ASKED, LESSON)
    assert lively["vocal_liveliness"] == 1.0 and flat["vocal_liveliness"] == delivery.FLOOR
    assert lively["responsiveness"] > flat["responsiveness"]


def test_camera_off_gives_a_voice_only_score():
    fractions, _ = delivery.score([voice_bin(n, pitch=LIVELY_PITCH) for n in range(8)], ASKED, LESSON)
    assert set(fractions) == {"vocal_liveliness", "emphasis", "responsiveness"}


def test_moments_count_more_than_duration():
    # Calm through most of the lesson; voice and face come alive only at the greeting,
    # at the question to the class, and when answering the student.
    key_bins = {0, 4, 6}
    bins = [
        camera_bin(n, pitch=LIVELY_PITCH if n in key_bins else FLAT_PITCH, face=LIVELY_FACE if n in key_bins else STILL_FACE, hands=0.3)
        for n in range(8)
    ]
    fractions, moments = delivery.score(bins, ASKED, LESSON)
    assert fractions["emphasis"] == 1.0
    assert fractions["facial_liveliness"] == 1.0  # warm at the right moments, not smiling for eight bins
    assert fractions["responsiveness"] == 1.0
    assert [m["t_ms"] for m in moments] == [0, 40_000, 60_000]
    assert moments[0] == {"t_ms": 0, "kind": "both", "text": "Pada 00:00 suara dan wajah Anda hidup saat menyapa murid."}


def test_a_still_face_and_flat_voice_throughout_is_the_low_end():
    fractions, moments = delivery.score([camera_bin(n) for n in range(8)], ASKED, LESSON)
    assert fractions["vocal_liveliness"] == fractions["facial_liveliness"] == delivery.FLOOR
    assert moments == []


def test_dark_stretches_are_left_out_not_counted_against_the_teacher():
    lively = [camera_bin(n, face=LIVELY_FACE, hands=0.3) for n in range(4)]
    dark = [camera_bin(n, face=0.0, hands=0.0, posture=0.0, visible=0.0, measured=False) for n in range(4, 8)]
    with_dark, _ = delivery.score(lively + dark, [], LESSON)
    without, _ = delivery.score(lively, [], LESSON)
    for key in ("facial_liveliness", "gestures", "posture"):
        assert with_dark[key] == without[key]


def test_gestures_reward_some_movement_and_posture_rewards_staying_in_frame():
    still, _ = delivery.score([camera_bin(n) for n in range(8)], [], LESSON)
    moving, _ = delivery.score([camera_bin(n, hands=0.3) for n in range(8)], [], LESSON)
    fidgeting, _ = delivery.score([camera_bin(n, hands=0.95) for n in range(8)], [], LESSON)
    away, _ = delivery.score([camera_bin(n, posture=0.2, visible=0.5) for n in range(8)], [], LESSON)
    assert moving["gestures"] == 1.0 > fidgeting["gestures"] > still["gestures"] == delivery.FLOOR
    assert moving["posture"] == 1.0 > away["posture"]


def test_no_bins_means_nothing_to_score():
    assert delivery.score([], ASKED, LESSON) == ({}, [])


def test_moments_never_name_an_emotion():
    bins = [camera_bin(n, pitch=LIVELY_PITCH, face=LIVELY_FACE) for n in range(8)]
    _, moments = delivery.score(bins, ASKED, LESSON)
    assert 0 < len(moments) <= delivery.MAX_MOMENTS
    assert not evidence.unkind(" ".join(m["text"] for m in moments))


def test_the_report_scores_the_card_voice_only_when_the_camera_is_off(db, lesson):
    user = db.get(User, lesson.user_id)
    user.tier = "institutional"
    db.add(user)
    for seq, piece in enumerate(LESSON * 3):  # enough speech to be read
        start = seq * 12_000
        db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start, end_ms=start + 9_000, text=piece.text))
    for n in range(14):
        db.add(SignalBin(session_id=lesson.id, t_start_ms=n * 10_000, pitch_variation=LIVELY_PITCH, volume=0.3))
    db.commit()

    report = scoring.build_report(db, lesson.id)
    card = next(d for d in report["dimensions"] if d["key"] == "delivery")

    assert card["available"] and card["score"] >= 80
    measured = {p["key"] for p in card["parameters"] if p["available"]}
    assert measured == {"vocal_liveliness", "emphasis"}  # no camera, and no student question in this lesson
    assert report["moments"] and all(m["kind"] == "voice" for m in report["moments"])


def test_a_locked_card_shows_no_moments(db, lesson):
    for seq, piece in enumerate(LESSON * 3):
        start = seq * 12_000
        db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start, end_ms=start + 9_000, text=piece.text))
    db.add(SignalBin(session_id=lesson.id, t_start_ms=0, pitch_variation=LIVELY_PITCH, volume=0.3))
    db.commit()
    report = scoring.build_report(db, lesson.id)  # free tier
    assert next(d for d in report["dimensions"] if d["key"] == "delivery")["locked"]
    assert report["moments"] == []
