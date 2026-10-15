"""Tone & expression: scored from the 10-second signal bins the browser sends.

The aim is to tell a lively delivery from a flat one without asking for
non-stop cheerfulness. Credit comes from voice and face coming alive at the
moments that matter: the greeting, a question to the class, answering a
student. Nothing here names an emotion, and lighting, camera quality and where
the eyes point are never scored.

What the browser puts in a bin (see frontend/src/features/simulator/vision):
  pitch_variation   spread of the voice's pitch within the bin, in semitones
  volume            average loudness, 0-1
  expressiveness    how far the face moved from the teacher's own neutral face, 0-1
  gesture_rate      share of the bin with the hands moving, 0-1
  posture_ok_pct    share of the bin sitting upright and in frame, 0-1
  face_visible_pct  share of the bin with the face found, 0-1
  measured          False when the picture was too dark to trust; camera values are then ignored
With the camera off only the two voice values are sent.
"""

import statistics

from app.models import Question, SignalBin, TranscriptSegment
from app.services import metrics
from app.services.rubric import band

BIN_MS = 10_000
GREETING_MS = 15_000  # the opening of the lesson
RESPONSE_MS = 5_000  # reacting to a student within this time counts as prompt

# Provisional until tuned on our labelled flat-versus-lively clips.
LIVELY_PITCH = 2.0  # semitones of pitch spread within a bin
LIVELY_FACE = 0.12
MOVING_HANDS = 0.10
FIDGETING = 0.90
LIFT = 1.15  # a key moment stands out when it is this far above the teacher's own middle value
QUIET_SHARE = 0.6  # a lift below the lively level still counts from this share of it upward

# Target bands (zero_low, full_low, full_high, zero_high) on the share of bins.
LIVELY_VOICE_BAND = (0.05, 0.40, 1, 2)
LIVELY_FACE_BAND = (0.05, 0.30, 1, 2)
KEY_MOMENT_BAND = (0, 0.50, 1, 2)
GESTURE_BAND = (0, 0.25, 1, 2)  # some hand movement in a quarter of the lesson is already full marks
FIDGET_SHARE = 0.90  # hands moving hard through nearly the whole lesson lowers it a little
POSTURE_BAND = (0.2, 0.7, 1, 2)

MAX_MOMENTS = 4
FLOOR = 0.2  # same floor as the other computed parameters


def score(
    bins: list[SignalBin], asked: list[Question], segments: list[TranscriptSegment]
) -> tuple[dict[str, float], list[dict]]:
    """Fraction of full marks per parameter that could be measured, and the lesson's liveliest moments."""
    voice = [b for b in bins if b.pitch_variation is not None]
    camera = [b for b in bins if b.measured and b.expressiveness is not None and (b.face_visible_pct or 0) > 0]
    found: dict[str, float] = {}
    keys = _key_moments(asked, segments)

    if voice:
        lively = sum(1 for b in voice if b.pitch_variation >= LIVELY_PITCH) / len(voice)
        found["vocal_liveliness"] = band(lively, *LIVELY_VOICE_BAND)
        lifted = _lifted(voice, keys)
        if lifted is not None:
            found["emphasis"] = band(lifted, *KEY_MOMENT_BAND)

    answered = [q for q in asked if q.answered_at_ms is not None]
    if answered and (voice or camera):
        found["responsiveness"] = statistics.mean(_response(q, voice, camera) for q in answered)

    if camera:
        lively = sum(1 for b in camera if b.expressiveness >= LIVELY_FACE) / len(camera)
        warm = _warm_moments(camera, keys)
        # A warm moment at the right time counts as much as a face that is lively throughout.
        found["facial_liveliness"] = max(band(lively, *LIVELY_FACE_BAND), warm if warm is not None else 0.0)
        moving = sum(1 for b in camera if (b.gesture_rate or 0) >= MOVING_HANDS) / len(camera)
        fidgeting = sum(1 for b in camera if (b.gesture_rate or 0) >= FIDGETING) / len(camera)
        found["gestures"] = band(moving, *GESTURE_BAND) * (0.6 if fidgeting >= FIDGET_SHARE else 1.0)
        upright = statistics.mean((b.posture_ok_pct or 0) * (b.face_visible_pct or 0) for b in camera)
        found["posture"] = band(upright, *POSTURE_BAND)

    fractions = {key: FLOOR + (1 - FLOOR) * value for key, value in found.items()}
    return fractions, _moments(voice, camera, keys)


def _key_moments(asked: list[Question], segments: list[TranscriptSegment]) -> list[tuple[int, str]]:
    """Times where a lift in voice or face means most, with a few words saying what happened there."""
    keys = [(0, "saat menyapa murid")] if segments else []
    keys += [(s.start_ms, "saat bertanya kepada murid") for s in segments if metrics.teacher_questions(s.text)]
    keys += [(q.answered_at_ms, "saat menjawab pertanyaan murid") for q in asked if q.answered_at_ms is not None]
    return sorted(keys)


def _bin_at(bins: list[SignalBin], t_ms: int) -> SignalBin | None:
    return next((b for b in bins if b.t_start_ms <= t_ms < b.t_start_ms + BIN_MS), None)


def _lifted(voice: list[SignalBin], keys: list[tuple[int, str]]) -> float | None:
    """Share of key moments where the voice rose above the teacher's own middle pitch spread or loudness."""
    middle_pitch = statistics.median(b.pitch_variation for b in voice)
    middle_volume = statistics.median((b.volume or 0) for b in voice)
    hits = total = 0
    for t_ms, _ in keys:
        at = _bin_at(voice, t_ms)
        if at is None:
            continue
        total += 1
        # Lively outright, or clearly above this teacher's own usual level (a quiet voice can still lift).
        lively = at.pitch_variation >= LIVELY_PITCH
        raised = at.pitch_variation >= middle_pitch * LIFT and at.pitch_variation >= LIVELY_PITCH * QUIET_SHARE
        louder = (at.volume or 0) >= middle_volume * LIFT > 0
        hits += lively or raised or louder
    return hits / total if total else None


def _warm_moments(camera: list[SignalBin], keys: list[tuple[int, str]]) -> float | None:
    """Share of key moments where the face was visibly alive. Only ever adds to the score."""
    hits = total = 0
    for t_ms, _ in keys:
        at = _bin_at(camera, t_ms)
        if at is None:
            continue
        total += 1
        hits += at.expressiveness >= LIVELY_FACE
    return band(hits / total, *KEY_MOMENT_BAND) if total else None


def _response(question: Question, voice: list[SignalBin], camera: list[SignalBin]) -> float:
    """How a student's question was met: answered promptly, and with voice or face alive while answering."""
    prompt = 1.0 if question.answered_at_ms - question.asked_at_ms <= RESPONSE_MS else 0.4
    v, c = _bin_at(voice, question.answered_at_ms), _bin_at(camera, question.answered_at_ms)
    signs = [v.pitch_variation >= LIVELY_PITCH] if v else []
    signs += [c.expressiveness >= LIVELY_FACE] if c else []
    alive = (1.0 if any(signs) else 0.3) if signs else prompt
    return 0.5 * prompt + 0.5 * alive


def _moments(voice: list[SignalBin], camera: list[SignalBin], keys: list[tuple[int, str]]) -> list[dict]:
    """The liveliest bins of the lesson, described by what was going on. Never an emotion word."""
    faces = {b.t_start_ms: b for b in camera}
    candidates = []
    for t_start in sorted({b.t_start_ms for b in voice} | set(faces)):
        v, c = _bin_at(voice, t_start), faces.get(t_start)
        voice_alive = bool(v and v.pitch_variation >= LIVELY_PITCH)
        face_alive = bool(c and c.expressiveness >= LIVELY_FACE)
        if not (voice_alive or face_alive):
            continue
        strength = (v.pitch_variation / LIVELY_PITCH if voice_alive else 0) + (c.expressiveness / LIVELY_FACE if face_alive else 0)
        context = next((what for t_ms, what in keys if t_start <= t_ms < t_start + BIN_MS), "saat menjelaskan")
        kind = "both" if voice_alive and face_alive else "voice" if voice_alive else "face"
        subject = {"both": "suara dan wajah Anda", "voice": "suara Anda", "face": "wajah Anda"}[kind]
        candidates.append((context != "saat menjelaskan", strength, t_start, kind, f"Pada {_clock(t_start)} {subject} hidup {context}."))
    best = sorted(candidates, reverse=True)[:MAX_MOMENTS]
    return [{"t_ms": t_start, "kind": kind, "text": text} for _, _, t_start, kind, text in sorted(best, key=lambda m: m[2])]


def _clock(ms: int) -> str:
    return f"{ms // 60_000:02d}:{ms // 1000 % 60:02d}"
