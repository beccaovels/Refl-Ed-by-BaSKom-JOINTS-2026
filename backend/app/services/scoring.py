"""Builds the report for a finished session.

Order of work: numbers first (metrics.py), then one LLM call that rates the
quoted parameters and drafts the feedback, then the evidence check, then the
card scores. The LLM never sets a card score: it gives a 1-5 level per
parameter and code turns levels into points.

With LLM_PROVIDER=fake the LLM call is replaced by a sample whose texts start
with "(Contoh)", so the Report page can be built with no key.
"""

import json
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
from app.services import delivery, evidence, examples, llm, metrics, profiles, rag
from app.services.metrics import SHARED_SCREEN, LessonMetrics
from app.services.questions import ASKING
from app.services.report_schema import ReportOut
from app.services.rubric import CARDS, FREE_CARDS, LABELS, Card, band, clarity_parameters, growth_label, worked_practice

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

MIN_WORDS = 40  # below this there is too little speech to say anything fair
MATERIAL_CHARS = 8_000
ANSWER_CHARS = 300
ANSWER_WINDOW_MS = 60_000  # what the teacher says in the minute after starting to answer
MAX_IDEAS = 3
MAX_STRENGTHS = 3
UNPROVEN_LEVEL = 3  # a 4 or 5 whose quote is not the teacher's own words drops to this
# "The working is not right" may only be said when the check named where: below this level needs a named step.
UNNAMED_SLIP_LEVEL = 3
FLOOR = 0.2  # a computed parameter at its lowest earns what level 1 earns, so both kinds share one scale
# Rated only when the teacher confirmed a photo of their own working and showed it.
EXAMPLE_PARAMETERS = ("worked_example", "worked_steps")

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


class ExampleFeedback(BaseModel):
    page: int
    kind: Literal["worked", "noticed"]
    text: str
    quote: str


class Assessment(BaseModel):
    """What the LLM returns for one lesson."""

    ratings: list[Rating]
    feedback: list[Feedback]
    summary: str
    ideas: list[IdeaDraft]
    example_feedback: list[ExampleFeedback] = Field(default_factory=list)


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
    events = list(db.exec(select(Question).where(Question.session_id == session_id).order_by(Question.asked_at_ms)))
    asked = [e for e in events if e.kind in ASKING]  # what students asked the teacher
    replies = [e for e in events if e.kind == "answer"]  # what students answered when the teacher asked
    reactions = {e.reply_to: e for e in events if e.kind == "reaction"}
    bins = list(db.exec(select(SignalBin).where(SignalBin.session_id == session_id).order_by(SignalBin.t_start_ms)))
    numbers = metrics.compute(db, session_id)
    answers = {q.id: _said_after(q.answered_at_ms, segments) for q in asked}
    answered = any(answers.values()) or bool(replies)
    worked = _example_rows(db, session, numbers)
    own_pages = {row["page"] for row in worked}
    # Only an example the teacher confirmed and showed counts: until confirmed, its text is our reading, not their words.
    counted = [row for row in worked if row["confirmed"] and row["shown_at_ms"] is not None]
    written = {row["page"]: _lines(row["reading"]) for row in counted}
    shown_at = {row["page"]: row["shown_at_ms"] for row in counted}

    enough_speech = numbers.words >= MIN_WORDS
    sample = llm.is_fake()
    assessment: Assessment | None = None
    wanted = _llm_parameters(profile, answered, counted)
    if enough_speech:
        if sample:
            assessment = _sample_assessment(wanted, counted)
        else:
            assessment = llm.generate_json(
                _prompt(db, session, profile, segments, asked, answers, replies, wanted, counted, own_pages), Assessment
            )

    levels = _levels(assessment, {p["key"] for p in wanted}, segments, written, sample, _slip_named(counted))
    fractions = {key: level / 5 for key, level in levels.items()}
    fractions.update(_computed(numbers, own_pages))
    signals, moments = delivery.score(bins, asked, segments)
    fractions.update(signals)

    items = _items(assessment, segments, written, shown_at, sample) if assessment else {}
    for key, extra in _computed_items(numbers, segments).items():
        items.setdefault(key, []).extend(extra)
    if assessment:
        for page, about in _example_items(assessment, segments, written, shown_at, sample).items():
            next(row for row in counted if row["page"] == page)["items"] = about

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
        "moments": moments if any(d["key"] == "delivery" and d["score"] is not None for d in dimensions) else [],
        "questions": _exchanges(asked, answers, replies, reactions, segments),
        "examples": worked,
    }
    return ReportOut.model_validate(report).model_dump()


# --- the LLM's part ---


def _llm_parameters(profile: dict, answered: bool, counted: list[dict]) -> list[dict]:
    """Every parameter the LLM rates for this lesson: key, card, title, what to look for."""
    first, second = clarity_parameters(profile)
    practice = " ".join(f"({n}) {p['look_for']}" for n, p in enumerate(worked_practice(profile), start=1))
    named = {
        "profile_a": first,
        "profile_b": second,
        "worked_steps": {"look_for": f"Pengerjaan contoh soal yang ditulis guru tertata dan dijelaskan. {practice}"},
    }
    wanted = []
    for card in CARDS:
        for p in card.parameters:
            if p.source != "llm":
                continue
            if p.key in ("answers_correct", "builds_on_questions") and not answered:
                continue  # no student question was answered, so there is nothing to rate
            if p.key in EXAMPLE_PARAMETERS and not counted:
                continue  # no worked example was confirmed and shown
            if p.key == "worked_example" and not any(_checked(row["check"]) for row in counted):
                continue  # the working could not be compared with anything, so its correctness is not rated
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
    replies: list[Question],
    wanted: list[dict],
    counted: list[dict],
    own_pages: set[int],
) -> str:
    exchanges = [
        (q.asked_at_ms, f"[{_clock(q.asked_at_ms)}] Murid bertanya: {q.text}\n  Jawaban guru: {answers[q.id] or '(belum dijawab)'}")
        for q in asked
    ] + [
        (
            r.asked_at_ms,
            f"[{_clock(r.asked_at_ms)}] Guru bertanya kepada kelas, lalu murid menjawab: {r.text}\n"
            f"  Guru melanjutkan: {_said_after(r.asked_at_ms, segments) or '(belum ada tanggapan)'}",
        )
        for r in replies
    ]
    focus = profile.get("accuracy_focus")
    seeds = profile.get("context_seeds") or ["kehidupan sehari-hari di sekitar murid"]
    return Template((PROMPT_DIR / "rubric.md").read_text(encoding="utf-8")).substitute(
        subject=session.subject,
        label=profile.get("label", session.class_name),
        chapter=" - ".join(part for part in (session.chapter, session.sub_chapter) if part),
        phase_expectation=profile.get("phase_expectation") or "(ikuti materi yang diunggah guru)",
        material=_material(db, session, own_pages) or "(guru tidak mengunggah materi; nilai dari konsistensi penjelasannya)",
        examples="\n\n".join(_shown_to_model(row) for row in counted) or "(guru tidak menampilkan contoh soal tulisan tangan)",
        transcript="\n".join(f"[{_clock(s.start_ms)}] {s.text}" for s in segments),
        student_questions="\n".join(text for _, text in sorted(exchanges)) or "(tidak ada pertanyaan murid)",
        parameters="\n".join(f"- `{p['key']}` ({p['title']}): {p['look_for']}" for p in wanted),
        accuracy_focus=f"- Untuk ketepatan isi pada mata pelajaran ini, perhatikan: {focus}" if focus else "",
        cards=", ".join(sorted({p["card"] for p in wanted})),
        context_seeds="; ".join(seeds),
    )


def _material(db: Session, session: TeachingSession, own_pages: set[int]) -> str:
    """Text of the slides the teacher showed, in the order first shown.

    The teacher's handwritten examples are left out: they are what is being
    looked at, not the reference to judge accuracy against.
    """
    if not session.material_id:
        return ""
    turns = db.exec(select(SlideEvent).where(SlideEvent.session_id == session.id).order_by(SlideEvent.t_ms)).all()
    pages = [page for page in dict.fromkeys(t.page for t in turns) or [1] if page not in own_pages and page != SHARED_SCREEN]
    text = "\n".join(f"[Halaman {page}] {rag.page_text(db, session.material_id, page)}" for page in pages)
    return text[:MATERIAL_CHARS]


def _levels(
    assessment: Assessment | None,
    wanted: set[str],
    segments: list[TranscriptSegment],
    written: dict[int, list[str]],
    sample: bool,
    slip_named: bool,
) -> dict[str, int]:
    """The level per parameter, after the evidence check."""
    levels: dict[str, int] = {}
    for rating in assessment.ratings if assessment else []:
        if rating.key not in wanted:
            continue  # only parameters that were asked for count
        level = rating.level
        if level > UNPROVEN_LEVEL and not sample and _said_or_wrote(rating.quote, segments, written) == (None, None):
            level = UNPROVEN_LEVEL
        if rating.key == "worked_example" and not slip_named:
            level = max(level, UNNAMED_SLIP_LEVEL)
        levels[rating.key] = level
    return levels


def _items(
    assessment: Assessment,
    segments: list[TranscriptSegment],
    written: dict[int, list[str]],
    shown_at: dict[int, int],
    sample: bool,
) -> dict[str, list[dict]]:
    """Feedback items per card. One `worked` and one `noticed` at most, each quoting the teacher's own words."""
    kept: dict[str, list[dict]] = {}
    for draft in assessment.feedback:
        t_ms, page = _said_or_wrote(draft.quote, segments, written)
        if t_ms is None and page is None and not sample:
            log.info("Dropped a feedback item: its quote is neither in the transcript nor in a confirmed example")
            continue
        if evidence.unkind(draft.text):
            log.info("Dropped a feedback item: wording rule")
            continue
        card_items = kept.setdefault(draft.dimension, [])
        if any(item["kind"] == draft.kind for item in card_items):
            continue
        when = shown_at[page] if page is not None else t_ms
        quote = evidence.unnumbered(draft.quote) if page is not None else draft.quote.strip()
        card_items.append(_item(draft.kind, draft.text.strip(), quote, when, page))
    return kept


def _example_items(
    assessment: Assessment,
    segments: list[TranscriptSegment],
    written: dict[int, list[str]],
    shown_at: dict[int, int],
    sample: bool,
) -> dict[int, list[dict]]:
    """Feedback on each worked example, by page: one `worked` and one `noticed` at most, the strength first.

    A quote may be a line the teacher wrote in that example, or something they said.
    """
    kept: dict[int, list[dict]] = {}
    for draft in assessment.example_feedback:
        if draft.page not in written or evidence.unkind(draft.text):
            continue
        wrote = evidence.find_written(draft.quote, {draft.page: written[draft.page]})
        t_ms = None if wrote else evidence.find_quote(draft.quote, segments)
        if wrote is None and t_ms is None and not sample:
            log.info("Dropped feedback on a worked example: its quote was neither written there nor said")
            continue
        about = kept.setdefault(draft.page, [])
        if any(item["kind"] == draft.kind for item in about):
            continue
        quote = evidence.unnumbered(draft.quote) if wrote else draft.quote.strip()
        about.append(_item(draft.kind, draft.text.strip(), quote, shown_at[draft.page] if wrote else t_ms, wrote))
    return {page: sorted(about, key=lambda item: item["kind"] != "worked") for page, about in kept.items()}


def _said_or_wrote(
    quote: str | None, segments: list[TranscriptSegment], written: dict[int, list[str]]
) -> tuple[int | None, int | None]:
    """Where a quote is the teacher's own: (when they said it, None), (None, page they wrote it on), or (None, None)."""
    t_ms = evidence.find_quote(quote, segments)
    if t_ms is not None:
        return t_ms, None
    return None, evidence.find_written(quote, written)


# --- the teacher's handwritten worked examples ---


def _example_rows(db: Session, session: TeachingSession, numbers: LessonMetrics) -> list[dict]:
    """The `examples` of the report: every photo of the material, with when and how long it was on stage."""
    if not session.material_id:
        return []
    turns = db.exec(select(SlideEvent).where(SlideEvent.session_id == session.id).order_by(SlideEvent.t_ms)).all()
    first_shown: dict[int, int] = {}
    for turn in turns:
        first_shown.setdefault(turn.page, turn.t_ms)
    on_stage = {slide["page"]: slide["ms"] for slide in numbers.time_per_slide}
    rows = []
    for example in examples.for_material(db, session.material_id):
        shown = examples.public(example)
        rows.append(
            {
                "example_id": example.id,
                "page": example.page,
                "shown_at_ms": first_shown.get(example.page),
                "shown_ms": on_stage.get(example.page, 0),
                "confirmed": example.status == "confirmed",
                "reading": shown["reading"],
                "check": shown["check"],
                "items": [],
            }
        )
    return rows


def _lines(reading: dict) -> list[str]:
    """Everything the teacher wrote in one example, a line each."""
    return [reading["question"], *(step["text"] for step in reading["steps"]), reading["final_answer"]]


def _checked(check: dict | None) -> bool:
    """True when the check could say anything at all about the working."""
    return bool(check) and (check["answer"] != "cannot_tell" or any(s["status"] != "cannot_tell" for s in check["steps"]))


def _slip_named(counted: list[dict]) -> bool:
    """True when a check points at a step, or at the final answer, to look at again."""
    return any(
        row["check"]["answer"] == "recheck" or any(step["status"] == "recheck" for step in row["check"]["steps"])
        for row in counted
        if row["check"]
    )


def _shown_to_model(row: dict) -> str:
    """One confirmed worked example as the rubric prompt sees it: what was written, and what the check found."""
    reading, check = row["reading"], row["check"]
    lines = [f"[Halaman {row['page']}, ditampilkan sejak {_clock(row['shown_at_ms'])}]", f"Soal: {reading['question'] or '(tidak tertulis)'}"]
    lines += [f"{step['n']}. {step['text']}" for step in reading["steps"]]
    lines.append(f"Jawaban akhir: {reading['final_answer'] or '(tidak tertulis)'}")
    notes = [f"langkah {step['n']}: {step['note']}" for step in check["steps"] if step["status"] == "recheck"]
    if check["answer"] == "recheck":
        notes.append("jawaban akhir berbeda dari hitungan kami" + (f" ({check['our_answer']})" if check["our_answer"] else ""))
    if notes:
        lines.append("Catatan pemeriksaan: " + "; ".join(notes))
    elif _checked(check):
        lines.append("Catatan pemeriksaan: langkah dan jawaban akhir sejalan dengan hitungan kami.")
    else:
        lines.append("Catatan pemeriksaan: tidak diperiksa.")
    return "\n".join(lines)


def _ideas(assessment: Assessment | None) -> list[dict]:
    ideas = []
    for draft in assessment.ideas if assessment else []:
        if evidence.unkind(draft.text) or evidence.banned_words(draft.ready_to_use):
            log.info("Dropped an idea: wording rule")
            continue
        ideas.append({"id": str(uuid4()), "text": draft.text.strip(), "ready_to_use": draft.ready_to_use.strip()})
    return ideas[:MAX_IDEAS]


def _sample_assessment(wanted: list[dict], counted: list[dict]) -> Assessment:
    """LLM_PROVIDER=fake: fixed levels and sample texts, so pages can be built with no key."""
    return Assessment(
        ratings=[Rating(key=p["key"], level=4) for p in wanted],
        example_feedback=[
            ExampleFeedback(
                page=row["page"],
                kind="worked",
                text="(Contoh) Pada tulisan Anda, banyaknya anggota ruang sampel ditulis lebih dulu, "
                "sehingga murid melihat dari mana angkanya berasal.",
                quote=row["reading"]["steps"][0]["text"] if row["reading"]["steps"] else row["reading"]["question"],
            )
            for row in counted
        ],
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


def _computed(numbers: LessonMetrics, own_pages: set[int] = frozenset()) -> dict[str, float]:
    """Fraction of full marks (0.2-1.0) for each computed parameter that could be measured.

    `own_pages` are the teacher's handwritten examples: a worked example rightly
    stays on stage a long time, so it is left out of how time is spread over slides.
    """
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
    slides = [slide["ms"] for slide in numbers.time_per_slide if slide["page"] not in own_pages]
    # time on the teacher's own working, or on a shared screen, is not time on any slide
    off_slides = numbers.shared_ms + sum(slide["ms"] for slide in numbers.time_per_slide if slide["page"] in own_pages)
    if len(slides) >= 2:
        found["slide_balance"] = band(max(slides) / max(numbers.duration_ms - off_slides, 1), *SLIDE_SHARE_BAND)

    return {key: FLOOR + (1 - FLOOR) * value for key, value in found.items()}


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


def _exchanges(
    asked: list[Question],
    answers: dict[str, str],
    replies: list[Question],
    reactions: dict[str | None, Question],
    segments: list[TranscriptSegment],
) -> list[dict]:
    """Every exchange with an AI student, in time order: their questions, and their answers to the teacher."""
    rows = []
    for q in asked:
        reaction = reactions.get(q.id)
        rows.append(
            {
                "event_id": q.id,
                "kind": q.kind,
                "persona": json.loads(q.persona) if q.persona else None,
                "text": q.text,
                "asked_at_ms": q.asked_at_ms,
                "level": q.level,
                "teacher_question": None,
                "answer_quote": answers[q.id] or None,
                "response_time_ms": q.answered_at_ms - q.asked_at_ms if q.answered_at_ms is not None else None,
                "satisfied": reaction.satisfied if reaction else None,
                "follow_up": reaction.text if reaction and reaction.satisfied is False else None,
            }
        )
    for r in replies:
        prompted_by = next((s for s in segments if s.start_ms == r.refers_to_ms), None)
        rows.append(
            {
                "event_id": r.id,
                "kind": r.kind,
                "persona": json.loads(r.persona) if r.persona else None,
                "text": r.text,
                "asked_at_ms": r.asked_at_ms,
                "level": None,
                "teacher_question": metrics.closing_question(prompted_by.text) if prompted_by else None,
                "answer_quote": _said_after(r.asked_at_ms, segments) or None,
                "response_time_ms": None,
                "satisfied": None,
                "follow_up": None,
            }
        )
    return sorted(rows, key=lambda row: row["asked_at_ms"])


def _said_after(start: int | None, segments: list[TranscriptSegment]) -> str:
    """What the teacher said in the minute from `start`, in their own words."""
    if start is None:
        return ""
    text =" ".join(s.text for s in segments if start <= s.start_ms < start + ANSWER_WINDOW_MS)
    return text[:ANSWER_CHARS].rsplit(" ", 1)[0] if len(text) > ANSWER_CHARS else text


def _item(kind: str, text: str, quote: str | None = None, t_ms: int | None = None, page: int | None = None) -> dict:
    """`page` is set when the quote is a line the teacher wrote; `t_ms` is then when that page was first shown."""
    return {"id": str(uuid4()), "kind": kind, "text": text, "quote": quote, "t_ms": t_ms, "page": page}


def _clock(ms: int) -> str:
    return f"{ms // 60_000:02d}:{ms // 1000 % 60:02d}"
