"""The AI students: when they speak, and what they say.

Called once per audio chunk and returns at most one event. The rules for when
are plain code; only the wording comes from the LLM, and every LLM step has a
canned fallback so the room never stalls.

What a student can do, in the order it is checked:
1. react    after the teacher answers a student's question: satisfied, or one polite follow-up
2. answer   when the teacher ends on a question to the class, one student answers it
3. ask      after enough teaching: a misconception question (once per lesson) or a regular one
A nudge is sent after a long silence, and a capstone question when the teacher ends the lesson.
"""

import json
import logging
import re
from pathlib import Path
from string import Template

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models import Question, SlideEvent, TeachingSession, TranscriptSegment
from app.services import llm, metrics, profiles, rag

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

DEMO_INTERVAL_MS = 75_000  # demo mode: a question every 60-90 s of speech
NORMAL_INTERVAL_MS = 240_000
SILENCE_NUDGE_MS = 30_000
WINDOW_MS = 120_000  # how much recent speech the model reads
SLIDE_CHARS = 1_500
MATERIAL_CHARS = 1_200
# The teacher is mid-lesson while this runs, so a slow provider is cut off.
LLM_TIMEOUT_S = 12

MIN_ANSWER_MS = 8_000  # the teacher has spoken this long since the question: time to react
MAX_ANSWER_MS = 40_000  # or this long has passed since they started answering
ANSWER_GAP_MS = 45_000  # at most one student answer to the teacher in this time
SAME_QUESTION = 0.6  # share of words in common above which two questions count as the same

ASKING = ("regular", "misconception", "capstone")  # a student asks the teacher something
DEFAULT_DEPTH = {"first": [1, 2], "later": [1, 2, 3], "max_level_3": 1, "note": ""}

STUDENT_NAMES = ["Dimas", "Sari", "Rizky"]
DEFAULT_STYLE = "Murid yang bertanya singkat dengan bahasa sehari-hari."

NUDGE_TEXT = "Silakan lanjutkan kapan pun Anda siap. Kami masih menyimak."

# Used with LLM_PROVIDER=fake, and when the provider fails. (text, depth level)
CANNED_QUESTIONS = [
    ("Maaf, boleh diberi satu contoh lagi untuk bagian yang tadi?", 1),
    ("Kalau di kehidupan sehari-hari, ini dipakainya untuk apa ya?", 2),
    ("Kenapa caranya harus seperti itu? Ada cara lain tidak?", 2),
]
CANNED_CAPSTONE = "Jadi kalau dirangkum dalam satu kalimat, hal terpenting dari pelajaran hari ini apa ya?"
CANNED_SATISFIED = "Oh begitu, sekarang saya paham. Terima kasih!"
CANNED_ANSWER = "(Contoh) Hmm, mungkin karena hasilnya bergantung pada nilai yang tadi, ya?"


# The prompts ask the model not to address the teacher as "Pak" or "Bu"; it sometimes does anyway.
_CALLING = re.compile(r",?\s+(Pak|Bu)(?=\s*[?.!,]|\s*$)")  # "..., Bu?" -> "...?"
_TITLE = re.compile(r"\b(Bapak|Ibu)\b(?!/)")  # "yang Bapak sebut" -> "yang Bapak/Ibu sebut"


class StudentQuestion(BaseModel):
    text: str = Field(min_length=5, description="Pertanyaan murid, satu atau dua kalimat pendek")
    refers_to_line: int = Field(description="Nomor baris transkrip yang ditanyakan")
    level: int = Field(default=1, ge=1, le=3, description="Tingkat kedalaman pertanyaan: 1, 2, atau 3")


class StudentAnswer(BaseModel):
    is_question: bool = Field(description="Apakah guru sungguh bertanya kepada kelas")
    text: str = Field(default="", description="Jawaban murid, atau teks kosong")


class StudentReaction(BaseModel):
    satisfied: bool = Field(description="Apakah jawaban guru sudah menjawab pertanyaan murid")
    text: str = Field(min_length=3, description="Tanda sudah paham, atau satu pertanyaan lanjutan yang sopan")


def next_event(db: Session, session_id: str, now_ms: int) -> dict | None:
    """The Event to send with this audio reply, or None.

    `now_ms` is the end_ms of the chunk that was just received, with or without speech in it.
    """
    session = _session(db, session_id)
    if session.status != "active":
        return None
    segments = _segments(db, session_id)
    events = _events(db, session_id)
    # Everything a student has asked the teacher, including a follow-up.
    asked = [e for e in events if e.kind in ASKING or (e.kind == "reaction" and e.satisfied is False)]
    last = asked[-1] if asked else None
    spoken_since = [s for s in segments if s.start_ms >= (last.asked_at_ms if last else 0)]

    # The first words after a student's question are the start of the answer.
    if last and last.answered_at_ms is None:
        if not spoken_since:
            return None
        last.answered_at_ms = spoken_since[0].start_ms
        db.add(last)
        db.commit()
    if any(e.kind == "capstone" for e in events):
        return None  # the lesson is closing; nothing more is asked

    # One nudge per silence: the next one needs speech in between.
    last_speech_ms = segments[-1].end_ms if segments else 0
    already_nudged = bool(events) and events[-1].kind == "nudge" and events[-1].asked_at_ms >= last_speech_ms
    if now_ms - last_speech_ms >= SILENCE_NUDGE_MS:
        if already_nudged:
            return None
        return _save(db, session, kind="nudge", text=NUDGE_TEXT, asked_at_ms=now_ms)

    # 1. A student's question is still open: wait for the answer, then react. Nothing else is asked meanwhile.
    reacted_to = {e.reply_to for e in events if e.kind == "reaction"}
    if last and last.id not in reacted_to:
        answer = [s for s in segments if s.start_ms >= last.answered_at_ms]
        answered_ms = sum(s.end_ms - s.start_ms for s in answer)
        if answered_ms >= MIN_ANSWER_MS or now_ms - last.answered_at_ms >= MAX_ANSWER_MS:
            return _react(db, session, last, answer, now_ms)
        return None

    # 2. The teacher just ended on a question to the class: one student answers.
    if segments and segments[-1].end_ms >= now_ms:
        question = metrics.closing_question(segments[-1].text)
        recent_answer = any(e.kind == "answer" and now_ms - e.asked_at_ms < ANSWER_GAP_MS for e in events)
        if question and not recent_answer:
            event = _answer(db, session, question, segments, len(events), now_ms)
            if event:
                return event

    # 3. Enough teaching since the last exchange: a student asks.
    since_ms = max((e.asked_at_ms for e in events if e.kind in ASKING or e.kind == "reaction"), default=0)
    taught = [s for s in segments if s.start_ms >= since_ms]
    interval = DEMO_INTERVAL_MS if session.demo_mode else NORMAL_INTERVAL_MS
    if not taught or sum(s.end_ms - s.start_ms for s in taught) < interval:
        return None
    return _ask(db, session, segments, [e for e in events if e.kind in ASKING], now_ms)


def capstone(db: Session, session_id: str) -> dict:
    """The one closing question, asked when the teacher presses "Selesai mengajar"."""
    session = _session(db, session_id)
    segments = _segments(db, session_id)
    events = _events(db, session_id)
    asked = [e for e in events if e.kind in ASKING]
    asked_at_ms = max(segments[-1].end_ms if segments else 0, events[-1].asked_at_ms if events else 0)
    persona = _persona(session, len(asked))
    profile = profiles.get(session.profile_id) or {}
    levels = (profile.get("question_depth") or DEFAULT_DEPTH)["later"]
    reply = _write(
        "capstone.md",
        StudentQuestion,
        session,
        persona,
        transcript=_lines(segments[-40:]),
        asked=_asked_list(asked),
        levels=_level_list(levels),
    )
    if reply and not _repeats(reply.text, asked):
        text, level = reply.text.strip(), _allowed(reply.level, levels)
        refers_to_ms = _line_ms(reply.refers_to_line, segments[-40:])
    else:
        text, level, refers_to_ms = CANNED_CAPSTONE, 1, None
    return _save(
        db, session, kind="capstone", text=text, asked_at_ms=asked_at_ms, refers_to_ms=refers_to_ms, persona=persona, level=level
    )


# --- what a student says ---


def _ask(db: Session, session: TeachingSession, segments: list[TranscriptSegment], asked: list[Question], now_ms: int) -> dict:
    """A misconception question once per lesson when its topic comes up; otherwise a regular one."""
    profile = profiles.get(session.profile_id) or {}
    persona = _persona(session, len(asked))
    recent = [s for s in segments if s.end_ms >= now_ms - WINDOW_MS]
    common = {"transcript": _lines(recent)}

    known = None if any(q.kind == "misconception" for q in asked) else _misconception(profile, recent)
    if known:
        reply = _write("misconception.md", StudentQuestion, session, persona, topic=known["topic"], misconception=known["misconception"], **common)
        text = reply.text.strip() if reply else known["ask"]
        return _save(
            db, session, kind="misconception", text=text, asked_at_ms=now_ms, persona=persona, level=2,
            refers_to_ms=_line_ms(reply.refers_to_line, recent) if reply else recent[-1].start_ms,
        )  # fmt: skip

    levels = _levels(profile, asked)
    depth = profile.get("question_depth") or DEFAULT_DEPTH
    slide, page = _slide(db, session)
    reply = _write(
        "question.md",
        StudentQuestion,
        session,
        persona,
        slide=slide or "(tidak ada materi yang ditampilkan)",
        material=_related(db, session, recent, page) or "(tidak ada)",
        asked=_asked_list(asked),
        assumed=_bullets(profile.get("assumed_knowledge")) or "(tidak ada catatan)",
        question_types=_bullets(profile.get("question_types")) or "- meminta contoh, alasan, atau arti istilah",
        levels=_level_list(levels),
        depth_note=depth.get("note", ""),
        examples=_bullets([e["text"] for e in profile.get("example_questions") or []]) or "(tidak ada contoh)",
        **common,
    )
    if reply and not _repeats(reply.text, asked):
        text, level, refers_to_ms = reply.text.strip(), _allowed(reply.level, levels), _line_ms(reply.refers_to_line, recent)
    else:
        unused = [c for c in CANNED_QUESTIONS if not _repeats(c[0], asked)] or CANNED_QUESTIONS
        (text, level), refers_to_ms = unused[0], recent[-1].start_ms
    return _save(
        db, session, kind="regular", text=text, asked_at_ms=now_ms, refers_to_ms=refers_to_ms, persona=persona, level=level
    )


def _answer(
    db: Session, session: TeachingSession, question: str, segments: list[TranscriptSegment], turn: int, now_ms: int
) -> dict | None:
    """One student answers the teacher's question, or None when it was not really a question to the class."""
    persona = _persona(session, turn + 1)  # not always the student who asks
    if llm.is_fake():
        text = CANNED_ANSWER
    else:
        profile = profiles.get(session.profile_id) or {}
        reply = _write(
            "answer.md",
            StudentAnswer,
            session,
            persona,
            transcript=_lines([s for s in segments if s.end_ms >= now_ms - WINDOW_MS]),
            question=question,
            assumed=_bullets(profile.get("assumed_knowledge")) or "(tidak ada catatan)",
        )
        if reply is None or not reply.is_question or not reply.text.strip():
            return None  # better silent than a made-up answer
        text = reply.text.strip()
    return _save(db, session, kind="answer", text=text, asked_at_ms=now_ms, refers_to_ms=segments[-1].start_ms, persona=persona)


def _react(db: Session, session: TeachingSession, question: Question, answer: list[TranscriptSegment], now_ms: int) -> dict:
    """The student shows the answer landed, or asks one follow-up. A follow-up is never followed by another."""
    persona = json.loads(question.persona) if question.persona else _persona(session, 0)
    satisfied, text = True, CANNED_SATISFIED
    if question.kind != "reaction":  # this is not already a follow-up
        reply = _write(
            "reaction.md",
            StudentReaction,
            session,
            persona,
            question=question.text,
            answer=" ".join(s.text for s in answer) or "(guru belum menjawab)",
        )
        if reply:
            satisfied, text = reply.satisfied, reply.text.strip()
    return _save(
        db, session, kind="reaction", text=text, asked_at_ms=now_ms, refers_to_ms=question.answered_at_ms,
        persona=persona, reply_to=question.id, satisfied=satisfied,
    )  # fmt: skip


def _write(prompt_file: str, schema: type[BaseModel], session: TeachingSession, persona: dict, **fields):
    """Fill a prompt file and ask the LLM. None with LLM_PROVIDER=fake or when the provider fails."""
    if llm.is_fake():
        return None
    profile = profiles.get(session.profile_id) or {}
    prompt = Template((PROMPT_DIR / prompt_file).read_text(encoding="utf-8")).substitute(
        name=persona["name"],
        style=persona["style"],
        label=profile.get("label", session.class_name),
        age=profile.get("student_persona", {}).get("age", "15-17"),
        subject=session.subject,
        chapter=" - ".join(part for part in (session.chapter, session.sub_chapter) if part),
        **fields,
    )
    try:
        return llm.generate_json(prompt, schema, timeout_s=LLM_TIMEOUT_S)
    except llm.LLMError as err:
        log.warning("%s failed, using the canned fallback: %s", prompt_file, err)
        return None


# --- choosing depth and topic ---


def _levels(profile: dict, asked: list[Question]) -> list[int]:
    """The depth levels the next regular question may use, from the profile's ladder."""
    depth = profile.get("question_depth") or DEFAULT_DEPTH
    levels = list(depth["first"] if len(asked) < 2 else depth["later"])
    limit = depth.get("max_level_3")
    if limit is not None and sum(1 for q in asked if q.level == 3) >= limit and len(levels) > 1:
        levels = [level for level in levels if level != 3] or levels
    return levels


def _allowed(level: int, levels: list[int]) -> int:
    """The level the model reported, moved to the nearest one this grade allows."""
    return min(levels, key=lambda allowed: (abs(allowed - level), allowed))


def _misconception(profile: dict, recent: list[TranscriptSegment]) -> dict | None:
    """The documented misconception whose topic the teacher has just reached, if any."""
    said = " ".join(s.text for s in recent).lower()
    latest, found = -1, None
    for known in profile.get("misconceptions") or []:
        # The topic mentioned last is the one being taught now.
        position = max((said.rfind(trigger.lower()) for trigger in known.get("triggers", [])), default=-1)
        if position > latest:
            latest, found = position, known
    return found


def _tidy(text: str) -> str:
    """A student's line without a guess at whether the teacher is a man or a woman."""
    text = _CALLING.sub("", text.strip())
    return _TITLE.sub("Bapak/Ibu", text)


def _repeats(text: str, asked: list[Question]) -> bool:
    """True when `text` shares most of its words with a question already asked."""
    words = set(metrics.words(text))
    for question in asked:
        other = set(metrics.words(question.text))
        if words and other and len(words & other) / len(words | other) >= SAME_QUESTION:
            return True
    return False


# --- material ---


def _slide(db: Session, session: TeachingSession) -> tuple[str, int | None]:
    """Text and number of the page on screen right now, from the last page turn."""
    if not session.material_id:
        return "", None
    turn = db.exec(
        select(SlideEvent).where(SlideEvent.session_id == session.id).order_by(SlideEvent.t_ms.desc())
    ).first()
    page = turn.page if turn else 1
    return rag.page_text(db, session.material_id, page)[:SLIDE_CHARS], page


def _related(db: Session, session: TeachingSession, recent: list[TranscriptSegment], page: int | None) -> str:
    """Parts of the teacher's material, off the current page, closest to what is being said."""
    if not session.material_id:
        return ""
    said = " ".join(s.text for s in recent)
    chunks = rag.closest_chunks(db, session.material_id, said, k=2, skip_page=page)
    return "\n".join(f"[Halaman {chunk.page}] {chunk.text}" for chunk in chunks)[:MATERIAL_CHARS]


# --- small helpers ---


def _lines(segments: list[TranscriptSegment]) -> str:
    return "\n".join(f"{line}. {s.text}" for line, s in enumerate(segments, start=1)) or "(belum ada)"


def _line_ms(line: int, segments: list[TranscriptSegment]) -> int | None:
    """Start time of the transcript line the model pointed at; the last line when the number is off."""
    if not segments:
        return None
    return segments[line - 1 if 1 <= line <= len(segments) else -1].start_ms


def _asked_list(asked: list[Question]) -> str:
    return "\n".join(f"- {q.text}" for q in asked) or "(belum ada)"


def _bullets(items: list[str] | None) -> str:
    return "\n".join(f"- {item}" for item in items or [])


def _level_list(levels: list[int]) -> str:
    return ", ".join(str(level) for level in levels)


def _session(db: Session, session_id: str) -> TeachingSession:
    session = db.get(TeachingSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    return session


def _segments(db: Session, session_id: str) -> list[TranscriptSegment]:
    return list(
        db.exec(
            select(TranscriptSegment).where(TranscriptSegment.session_id == session_id).order_by(TranscriptSegment.seq)
        )
    )


def _events(db: Session, session_id: str) -> list[Question]:
    return list(db.exec(select(Question).where(Question.session_id == session_id).order_by(Question.asked_at_ms)))


def _persona(session: TeachingSession, index: int) -> dict:
    profile = profiles.get(session.profile_id) or {}
    style = profile.get("student_persona", {}).get("style", DEFAULT_STYLE)
    return {"name": STUDENT_NAMES[index % len(STUDENT_NAMES)], "style": style}


def _save(
    db: Session,
    session: TeachingSession,
    *,
    kind: str,
    text: str,
    asked_at_ms: int,
    refers_to_ms: int | None = None,
    persona: dict | None = None,
    level: int | None = None,
    reply_to: str | None = None,
    satisfied: bool | None = None,
) -> dict:
    question = Question(
        session_id=session.id,
        kind=kind,
        persona=json.dumps(persona, ensure_ascii=False) if persona else None,
        text=text if kind == "nudge" else _tidy(text),
        asked_at_ms=asked_at_ms,
        refers_to_ms=refers_to_ms,
        level=level,
        reply_to=reply_to,
        satisfied=satisfied,
    )
    db.add(question)
    db.commit()
    return to_event(question)


def to_event(question: Question) -> dict:
    """A stored event in the Event shape of docs/api-contract.md."""
    return {
        "id": question.id,
        "kind": question.kind,
        "persona": json.loads(question.persona) if question.persona else None,
        "text": question.text,
        "asked_at_ms": question.asked_at_ms,
        "refers_to_ms": question.refers_to_ms,
        "level": question.level,
        "question_id": question.reply_to,
        "satisfied": question.satisfied,
    }
