"""Builds the report for a finished session.

Order of work: numbers first (metrics.py), then one LLM call that rates the
quoted parameters and drafts the feedback, then the evidence check, then the
card scores. The LLM never sets a card score: it gives a 1-5 level per
parameter and code turns levels into points.

With LLM_PROVIDER=fake the LLM call is replaced by a sample whose texts start
with "(Contoh)", so the Report page can be built with no key.
"""

import logging
import statistics
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models import Question, SignalBin, SlideEvent, TeachingSession, TranscriptSegment, User
from app.services import evidence, llm, metrics, profiles, rag
from app.services.metrics import LessonMetrics
from app.services.report_schema import ReportOut
from app.services.rubric import CARDS, FREE_CARDS, LABELS, Card, band, clarity_parameters, growth_label

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

MIN_WORDS = 40  # below this there is too little speech to say anything fair
MATERIAL_CHARS = 8_000
ANSWER_CHARS = 300
ANSWER_WINDOW_MS = 60_000  # what the teacher says in the minute after starting to answer
MAX_IDEAS = 3
MAX_STRENGTHS = 3
UNPROVEN_LEVEL = 3  # a 4 or 5 whose quote is not in the transcript drops to this
FLOOR = 0.2  # a computed parameter at its lowest earns what level 1 earns, so both kinds share one scale

# Target bands (zero_low, full_low, full_high, zero_high). Provisional until tuned on our labelled clips.
WPM_BAND = (60, 100, 160, 210)
QUESTIONS_PER_MIN_BAND = (0, 0.5, 99, 100)  # one question every two minutes or more
PAUSES_PER_MIN_BAND = (0, 1, 6, 12)
PACE_VARIATION_BAND = (0.03, 0.15, 9, 10)  # spread of pace between audio pieces
READING_BAND = (-1, 0, 0.15, 0.6)  # share read from the slide
SLIDE_SHARE_BAND = (-1, 0, 0.5, 0.9)  # share of the lesson spent on the longest slide

TOO_SHORT = "Rekaman terlalu singkat untuk dibaca dengan adil."
NO_SIGNALS = "Belum ada sinyal suara atau kamera untuk sesi ini."
SHORT_SUMMARY = (
    "Sesi ini masih terlalu singkat untuk kami beri masukan yang adil. "
    "Anda bisa mencoba berlatih beberapa menit lebih lama, lalu melihat laporannya lagi."
)


class Rating(BaseModel):
    key: str
    level: int = Field(ge=1, le=5)
    quote: str = ""


class Feedback(BaseModel):
    dimension: str
    kind: Literal["worked", "noticed"]
    text: str
    quote: str


class IdeaDraft(BaseModel):
    text: str
    ready_to_use: str


class Assessment(BaseModel):
    """What the LLM returns for one lesson."""

    ratings: list[Rating]
    feedback: list[Feedback]
    summary: str
    ideas: list[IdeaDraft]


def build_report(db: Session, session_id: str) -> dict:
    """The full `Report` of docs/api-contract.md for one session.

    Raises ValueError for an unknown session and llm.LLMError when no provider answered.
    """
    session = db.get(TeachingSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    user = db.get(User, session.user_id)
    institutional = user is not None and user.tier == "institutional"
    profile = profiles.get(session.profile_id) or {}
    segments = list(
        db.exec(select(TranscriptSegment).where(TranscriptSegment.session_id == session_id).order_by(TranscriptSegment.seq))
    )
    asked = list(
        db.exec(
            select(Question).where(Question.session_id == session_id, Question.kind != "nudge").order_by(Question.asked_at_ms)
        )
    )
    bins = list(db.exec(select(SignalBin).where(SignalBin.session_id == session_id).order_by(SignalBin.t_start_ms)))
    numbers = metrics.compute(db, session_id)
    answers = {q.id: _answer(q, segments) for q in asked}
    answered = any(answers.values())

    enough_speech = numbers.words >= MIN_WORDS
    sample = llm.is_fake()
    assessment: Assessment | None = None
    wanted = _llm_parameters(profile, answered)
    if enough_speech:
        if sample:
            assessment = _sample_assessment(wanted)
        else:
            assessment = llm.generate_json(
                _prompt(db, session, profile, segments, asked, answers, wanted), Assessment
            )

    levels = _levels(assessment, {p["key"] for p in wanted}, segments, sample)
    fractions = {key: level / 5 for key, level in levels.items()}
    fractions.update(_computed(numbers))
    fractions.update(_delivery(bins, asked))

    items = _items(assessment, segments, sample) if assessment else {}
    for key, extra in _computed_items(numbers, segments).items():
        items.setdefault(key, []).extend(extra)

    dimensions = []
    for card in CARDS:
        locked = card.key not in FREE_CARDS and not institutional
        dimensions.append(_dimension(card, profile, fractions, items.get(card.key, []), locked, enough_speech))

    counted = [d for d in dimensions if d["score"] is not None]
    overall = round(sum(d["score"] * d["weight"] for d in counted) / sum(d["weight"] for d in counted)) if counted else None
    strengths = _strengths(dimensions, numbers)
    ideas = _ideas(assessment)
    summary = assessment.summary.strip() if assessment else SHORT_SUMMARY
    if evidence.unkind(summary):
        log.warning("Summary broke a wording rule; replaced with a plain one")
        summary = strengths[0]["text"]

    report = {
        "id": str(uuid4()),
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": {"id": session.profile_id, "label": profile.get("label", session.class_name)},
        "overall": {
            "score": overall,
            "label": growth_label(overall) if overall is not None else None,
            "label_text": LABELS[growth_label(overall)] if overall is not None else None,
            "summary": summary,
        },
        "strengths": strengths,
        "dimensions": dimensions,
        "ideas": ideas,
        "tip": ideas[0]["text"] if ideas else None,
        "metrics": numbers.public(),
        "moments": [],
        "questions": [
            {
                "event_id": q.id,
                "kind": q.kind,
                "text": q.text,
                "asked_at_ms": q.asked_at_ms,
                "answer_quote": answers[q.id] or None,
                "response_time_ms": q.answered_at_ms - q.asked_at_ms if q.answered_at_ms is not None else None,
            }
            for q in asked
        ],
    }
    return ReportOut.model_validate(report).model_dump()


# --- the LLM's part ---


def _llm_parameters(profile: dict, answered: bool) -> list[dict]:
    """Every parameter the LLM rates for this lesson: key, card, title, what to look for."""
    first, second = clarity_parameters(profile)
    named = {"profile_a": first, "profile_b": second}
    wanted = []
    for card in CARDS:
        for p in card.parameters:
            if p.source != "llm":
                continue
            if p.key in ("answers_correct", "builds_on_questions") and not answered:
                continue  # no student question was answered, so there is nothing to rate
            custom = named.get(p.key, {})
            wanted.append(
                {
                    "key": p.key,
                    "card": card.key,
                    "title": custom.get("title", p.title),
                    "look_for": custom.get("look_for", p.look_for),
                }
            )
    return wanted


def _prompt(
    db: Session,
    session: TeachingSession,
    profile: dict,
    segments: list[TranscriptSegment],
    asked: list[Question],
    answers: dict[str, str],
    wanted: list[dict],
) -> str:
    focus = profile.get("accuracy_focus")
    seeds = profile.get("context_seeds") or ["kehidupan sehari-hari di sekitar murid"]
    return Template((PROMPT_DIR / "rubric.md").read_text(encoding="utf-8")).substitute(
        subject=session.subject,
        label=profile.get("label", session.class_name),
        chapter=" - ".join(part for part in (session.chapter, session.sub_chapter) if part),
        phase_expectation=profile.get("phase_expectation") or "(ikuti materi yang diunggah guru)",
        material=_material(db, session) or "(guru tidak mengunggah materi; nilai dari konsistensi penjelasannya)",
        transcript="\n".join(f"[{_clock(s.start_ms)}] {s.text}" for s in segments),
        student_questions="\n".join(
            f"[{_clock(q.asked_at_ms)}] Murid: {q.text}\n  Jawaban guru: {answers[q.id] or '(belum dijawab)'}" for q in asked
        )
        or "(tidak ada pertanyaan murid)",
        parameters="\n".join(f"- `{p['key']}` ({p['title']}): {p['look_for']}" for p in wanted),
        accuracy_focus=f"- Untuk ketepatan isi pada mata pelajaran ini, perhatikan: {focus}" if focus else "",
        cards=", ".join(sorted({p["card"] for p in wanted})),
        context_seeds="; ".join(seeds),
    )


def _material(db: Session, session: TeachingSession) -> str:
    """Text of the pages the teacher showed, in the order first shown."""
    if not session.material_id:
        return ""
    turns = db.exec(select(SlideEvent).where(SlideEvent.session_id == session.id).order_by(SlideEvent.t_ms)).all()
    pages = list(dict.fromkeys(t.page for t in turns)) or [1]
    text = "\n".join(f"[Halaman {page}] {rag.page_text(db, session.material_id, page)}" for page in pages)
    return text[:MATERIAL_CHARS]


def _levels(
    assessment: Assessment | None, wanted: set[str], segments: list[TranscriptSegment], sample: bool
) -> dict[str, int]:
    """The level per parameter, after the evidence check."""
    levels: dict[str, int] = {}
    for rating in assessment.ratings if assessment else []:
        if rating.key not in wanted:
            continue  # only parameters that were asked for count
        level = rating.level
        if level > UNPROVEN_LEVEL and not sample and evidence.find_quote(rating.quote, segments) is None:
            level = UNPROVEN_LEVEL
        levels[rating.key] = level
    return levels


def _items(assessment: Assessment, segments: list[TranscriptSegment], sample: bool) -> dict[str, list[dict]]:
    """Feedback items per card. One `worked` and one `noticed` at most, each with a quote that exists."""
    kept: dict[str, list[dict]] = {}
    for draft in assessment.feedback:
        t_ms = evidence.find_quote(draft.quote, segments)
        if t_ms is None and not sample:
            log.info("Dropped a feedback item: its quote is not in the transcript")
            continue
        if evidence.unkind(draft.text):
            log.info("Dropped a feedback item: wording rule")
            continue
        card_items = kept.setdefault(draft.dimension, [])
        if any(item["kind"] == draft.kind for item in card_items):
            continue
        card_items.append(_item(draft.kind, draft.text.strip(), draft.quote.strip(), t_ms))
    return kept


def _ideas(assessment: Assessment | None) -> list[dict]:
    ideas = []
    for draft in assessment.ideas if assessment else []:
        if evidence.unkind(draft.text) or evidence.banned_words(draft.ready_to_use):
            log.info("Dropped an idea: wording rule")
            continue
        ideas.append({"id": str(uuid4()), "text": draft.text.strip(), "ready_to_use": draft.ready_to_use.strip()})
    return ideas[:MAX_IDEAS]


def _sample_assessment(wanted: list[dict]) -> Assessment:
    """LLM_PROVIDER=fake: fixed levels and sample texts, so pages can be built with no key."""
    return Assessment(
        ratings=[Rating(key=p["key"], level=4) for p in wanted],
        feedback=[
            Feedback(
                dimension="engagement",
                kind="worked",
                text="(Contoh) Pada 02:15 Anda membandingkan lintasan bola dengan grafik fungsi kuadrat. "
                "Perbandingan seperti ini mudah diingat murid.",
                quote="coba bayangkan bola yang dilempar ke atas, lintasannya melengkung",
            ),
            Feedback(
                dimension="engagement",
                kind="noticed",
                text="(Contoh) Dari 04:00 sampai 06:30 penjelasan mengikuti teks pada salindia dengan sangat dekat.",
                quote="bentuk umumnya adalah a x kuadrat ditambah b x ditambah c",
            ),
            Feedback(
                dimension="clarity",
                kind="worked",
                text="(Contoh) Pada 01:10 Anda menjelaskan arti istilah baru sebelum memakainya.",
                quote="lengkungan seperti itu kita sebut parabola",
            ),
        ],
        summary="(Contoh) Pembuka Anda dengan lintasan bola langsung menghubungkan materi dengan keseharian murid. "
        "Terima kasih sudah meluangkan waktu berlatih. Anda bisa mencoba memberi jeda sejenak setelah bertanya.",
        ideas=[
            IdeaDraft(
                text="(Contoh) Satu ide: buka pelajaran dengan pertanyaan pemantik dari keseharian murid.",
                ready_to_use="Pernahkah kalian memperhatikan air mancur di alun-alun? "
                "Kenapa airnya selalu jatuh membentuk lengkungan yang sama?",
            )
        ],
    )


# --- the computed part ---


def _computed(numbers: LessonMetrics) -> dict[str, float]:
    """Fraction of full marks (0.2-1.0) for each computed parameter that could be measured."""
    minutes = numbers.duration_ms / 60_000
    found: dict[str, float] = {}
    if minutes <= 0 or numbers.words < MIN_WORDS:
        return found

    asking = band(numbers.questions_asked / minutes, *QUESTIONS_PER_MIN_BAND)
    thinking = metrics.thinking_time_share(numbers.wait_times_ms)
    found["invites_students"] = asking if thinking is None else 0.6 * asking + 0.4 * thinking
    if numbers.reading_share is not None:
        found["own_words"] = band(numbers.reading_share, *READING_BAND)

    found["speaking_rate"] = band(numbers.words_per_minute, *WPM_BAND)
    pausing = band(numbers.pause_count / minutes, *PAUSES_PER_MIN_BAND)
    found["pauses"] = pausing if thinking is None else (pausing + thinking) / 2
    if len(numbers.segment_wpm) >= 4:
        spread = statistics.pstdev(numbers.segment_wpm) / max(statistics.mean(numbers.segment_wpm), 1)
        found["pace_variation"] = band(spread, *PACE_VARIATION_BAND)
    if len(numbers.time_per_slide) >= 2:
        longest = max(slide["ms"] for slide in numbers.time_per_slide)
        found["slide_balance"] = band(longest / max(numbers.duration_ms, 1), *SLIDE_SHARE_BAND)

    return {key: FLOOR + (1 - FLOOR) * value for key, value in found.items()}


def _delivery(bins: list[SignalBin], asked: list[Question]) -> dict[str, float]:
    """Voice and on-camera parameters from the signal bins. Filled in with the vision milestone."""
    return {}


def _computed_items(numbers: LessonMetrics, segments: list[TranscriptSegment]) -> dict[str, list[dict]]:
    """Feedback that comes straight from the numbers. Observations only, with the moment they refer to."""
    items: dict[str, list[dict]] = {}
    if numbers.words < MIN_WORDS:
        return items
    for segment in segments:
        asked = metrics.teacher_questions(segment.text)
        if asked:
            items.setdefault("engagement", []).append(
                _item(
                    "worked",
                    f"Anda mengajukan {numbers.questions_asked} pertanyaan kepada murid, "
                    f"yang pertama pada {_clock(segment.start_ms)}. Pertanyaan mengajak murid ikut berpikir.",
                    asked[0],
                    segment.start_ms,
                )
            )
            break
    if numbers.reading_share is not None and numbers.reading_share >= 0.4:
        items.setdefault("engagement", []).append(
            _item("noticed", f"Sekitar {round(numbers.reading_share * 100)}% penjelasan mengikuti teks salindia dengan sangat dekat.")
        )
    low, high = WPM_BAND[1], WPM_BAND[2]
    pace_kind = "worked" if low <= numbers.words_per_minute <= high else "noticed"
    pace = f"Rata-rata Anda berbicara {numbers.words_per_minute} kata per menit"
    pace_note = (
        f"{pace}, tempo yang nyaman diikuti murid."
        if pace_kind == "worked"
        else f"{pace}. Sebagai gambaran, {low}-{high} kata per menit umumnya nyaman diikuti murid."
    )
    items.setdefault("pacing", []).append(_item(pace_kind, pace_note))
    return items


# --- putting the report together ---


def _dimension(card: Card, profile: dict, fractions: dict[str, float], items: list[dict], locked: bool, enough: bool) -> dict:
    first, second = clarity_parameters(profile)
    titles = {"profile_a": first["title"], "profile_b": second["title"]}
    parameters = []
    for p in card.parameters:
        fraction = fractions.get(p.key)
        parameters.append(
            {
                "key": p.key,
                "title": titles.get(p.key, p.title),
                "score": round(fraction * p.max, 1) if fraction is not None else None,
                "max": p.max,
                "available": fraction is not None,
                "source": p.source,
            }
        )
    measured = [p for p in parameters if p["available"]]
    available = bool(measured)
    # A parameter that could not be measured gives its weight to the rest of the card.
    score = round(sum(p["score"] for p in measured) / sum(p["max"] for p in measured) * 100) if measured else None
    reason = None
    if not available:
        reason = NO_SIGNALS if card.key == "delivery" and enough else TOO_SHORT
    shown = available and not locked
    kinds = {"worked": 0, "noticed": 1}
    return {
        "key": card.key,
        "title": card.title,
        "score": score if shown else None,
        "label": growth_label(score) if shown else None,
        "label_text": LABELS[growth_label(score)] if shown else None,
        "weight": card.weight,
        "available": available,
        "locked": locked,
        "unavailable_reason": reason,
        "parameters": parameters if shown else [],
        "items": _one_of_each(sorted(items, key=lambda item: kinds[item["kind"]])) if shown else [],
    }


def _one_of_each(items: list[dict]) -> list[dict]:
    """At most one `worked` and one `noticed` per card, the strength first."""
    kept: dict[str, dict] = {}
    for item in items:
        kept.setdefault(item["kind"], item)
    return list(kept.values())


def _strengths(dimensions: list[dict], numbers: LessonMetrics) -> list[dict]:
    """What the report opens with: the `worked` item of the strongest cards. Never empty."""
    ranked = sorted((d for d in dimensions if d["score"] is not None), key=lambda d: -d["score"])
    worked = [item for d in ranked for item in d["items"] if item["kind"] == "worked"]
    # The teacher's own words come before a plain number.
    strengths = sorted(worked, key=lambda item: item["quote"] is None)[:MAX_STRENGTHS]
    if not strengths:
        strengths = [
            _item("worked", f"Anda menyelesaikan satu sesi latihan selama {_clock(numbers.duration_ms)}. Meluangkan waktu berlatih sudah langkah nyata.")
        ]
    return strengths


def _answer(question: Question, segments: list[TranscriptSegment]) -> str:
    """What the teacher said right after a student's question, in their own words."""
    if question.answered_at_ms is None:
        return ""
    start = question.answered_at_ms
    text = " ".join(s.text for s in segments if start <= s.start_ms < start + ANSWER_WINDOW_MS)
    return text[:ANSWER_CHARS].rsplit(" ", 1)[0] if len(text) > ANSWER_CHARS else text


def _item(kind: str, text: str, quote: str | None = None, t_ms: int | None = None) -> dict:
    return {"id": str(uuid4()), "kind": kind, "text": text, "quote": quote, "t_ms": t_ms}


def _clock(ms: int) -> str:
    return f"{ms // 60_000:02d}:{ms // 1000 % 60:02d}"
