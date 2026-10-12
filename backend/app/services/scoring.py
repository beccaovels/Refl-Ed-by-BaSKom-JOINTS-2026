"""Builds the report for a finished session.

For now this returns a sample report with the exact shape of `Report` in
docs/api-contract.md, so the Report page can be built. Session facts (tier,
camera, questions asked) are real; scores and feedback text are samples and
every sample text starts with "(Contoh)".
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Session, select

from app.models import Question, TeachingSession, User

FREE_DIMENSIONS = {"content_accuracy", "teaching_flow", "clarity", "engagement"}


def growth_label(score: float) -> str:
    if score < 2.5:
        return "starting"
    if score < 4:
        return "developing"
    return "strong"


def build_report(db: Session, session_id: str) -> dict:
    session = db.get(TeachingSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    user = db.get(User, session.user_id)
    institutional = user is not None and user.tier == "institutional"
    asked = db.exec(
        select(Question)
        .where(Question.session_id == session_id, Question.kind != "nudge")
        .order_by(Question.asked_at_ms)
    ).all()

    worked = _item(
        "worked",
        "(Contoh) Pada 02:15 Anda membandingkan lintasan bola dengan grafik fungsi kuadrat. "
        "Perbandingan seperti ini mudah diingat murid.",
        quote="coba bayangkan bola yang dilempar ke atas, lintasannya melengkung",
        t_ms=135_000,
    )
    noticed = _item(
        "noticed",
        "(Contoh) Dari 04:00 sampai 06:30 penjelasan mengikuti teks pada salindia dengan sangat dekat.",
        t_ms=240_000,
    )
    sample_scores = {
        "content_accuracy": 4.0,
        "teaching_flow": 3.5,
        "clarity": 4.0,
        "engagement": 3.0,
        "pacing": 4.5,
        "on_camera_presence": 4.0,
    }
    dimensions = []
    for key, score in sample_scores.items():
        available = key != "on_camera_presence" or session.camera_on
        locked = key not in FREE_DIMENSIONS and not institutional
        shown = available and not locked
        dimensions.append(
            {
                "key": key,
                "score": score if shown else None,
                "label": growth_label(score) if shown else None,
                "available": available,
                "locked": locked,
                "items": [worked, noticed] if shown and key == "engagement" else [],
            }
        )
    scored = [d["score"] for d in dimensions if d["score"] is not None]
    overall = round(sum(scored) / len(scored), 1)

    return {
        "id": str(uuid4()),
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "overall": {"score": overall, "label": growth_label(overall)},
        "strengths": [worked],
        "dimensions": dimensions,
        "ideas": [
            {
                "id": str(uuid4()),
                "text": "(Contoh) Satu ide: buka pelajaran dengan pertanyaan pemantik dari keseharian murid.",
                "ready_to_use": "Pernahkah kalian memperhatikan air mancur di alun-alun? "
                "Kenapa airnya selalu jatuh membentuk lengkungan yang sama?",
            }
        ],
        "metrics": {
            "words_per_minute": 128,
            "pause_count": 14,
            "questions_asked": 3,
            "wait_time_avg_ms": 2400,
            "reading_share": 0.22 if session.material_id else None,
            "response_time_avg_ms": 3100 if asked else None,
            "time_per_slide": [{"page": 1, "ms": 95_000}, {"page": 2, "ms": 140_000}] if session.material_id else [],
        },
        "questions": [
            {"event_id": q.id, "kind": q.kind, "text": q.text, "asked_at_ms": q.asked_at_ms, "answer_quote": None}
            for q in asked
        ],
    }


def _item(kind: str, text: str, quote: str | None = None, t_ms: int | None = None) -> dict:
    return {"id": str(uuid4()), "kind": kind, "text": text, "quote": quote, "t_ms": t_ms}
