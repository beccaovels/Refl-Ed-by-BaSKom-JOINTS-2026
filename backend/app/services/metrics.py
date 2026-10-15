"""Numbers measured from the lesson itself. No LLM: the same lesson always gives the same numbers.

Everything is computed from transcript timestamps, page turns and the AI
students' questions. `compute()` loads a session; the functions below it take
plain lists so they can be tested with fixed timestamps.
"""

import re
from dataclasses import dataclass, field

from sqlmodel import Session, select

from app.models import Question, SlideEvent, TeachingSession, TranscriptSegment
from app.services import rag

PAUSE_MS = 2_000  # a gap this long between two audio pieces is a pause
THINKING_TIME_MS = 3_000  # a pause this long after a question gives students time to think
READ_NGRAM = 5  # words in a row shared with the slide
READ_RUN = 8  # only stretches at least this long count as reading; a definition read out is normal

FILLERS = re.compile(r"\b(e{2,}|em{2,}|hm+|anu|apa ya|gitu)\b")
# Sentences that are questions even when the transcript has no question mark, so the
# count does not depend on Whisper's punctuation. A sentence counts when it starts with one of these.
QUESTION_OPENERS = (
    "apa", "apakah", "siapa", "siapakah", "kapan", "berapa", "berapakah", "di mana", "dimana", "manakah",
    "kenapa", "mengapa", "bagaimana", "bagaimanakah", "gimana",
    "bisakah", "adakah", "bukankah", "benarkah", "mungkinkah", "dapatkah", "bolehkah",
    "ada yang tahu", "ada yang bisa", "ada yang ingat", "ada yang mau", "coba siapa", "menurut kalian", "kira-kira",
)  # fmt: skip
_OPENER = re.compile(r"^(" + "|".join(re.escape(opener) for opener in QUESTION_OPENERS) + r")\b")


@dataclass
class LessonMetrics:
    duration_ms: int = 0
    words: int = 0
    words_per_minute: int = 0
    pause_count: int = 0
    questions_asked: int = 0
    wait_times_ms: list[int] = field(default_factory=list)  # pause after each teacher question
    response_times_ms: list[int] = field(default_factory=list)  # time to start answering each AI student
    filler_count: int = 0
    reading_share: float | None = None  # None without material
    time_per_slide: list[dict] = field(default_factory=list)
    segment_wpm: list[int] = field(default_factory=list)  # pace of each audio piece, for pace variation

    def public(self) -> dict:
        """The `metrics` object of Report in docs/api-contract.md."""
        return {
            "words_per_minute": self.words_per_minute,
            "pause_count": self.pause_count,
            "questions_asked": self.questions_asked,
            "wait_time_avg_ms": _mean(self.wait_times_ms),
            "reading_share": self.reading_share,
            "response_time_avg_ms": _mean(self.response_times_ms),
            "filler_count": self.filler_count,
            "time_per_slide": self.time_per_slide,
        }


def compute(db: Session, session_id: str) -> LessonMetrics:
    session = db.get(TeachingSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    segments = list(
        db.exec(select(TranscriptSegment).where(TranscriptSegment.session_id == session_id).order_by(TranscriptSegment.seq))
    )
    turns = list(db.exec(select(SlideEvent).where(SlideEvent.session_id == session_id).order_by(SlideEvent.t_ms)))
    # Only what a student asked the teacher: not nudges, and not a student's reply to the teacher.
    asked = list(
        db.exec(
            select(Question).where(
                Question.session_id == session_id, Question.kind.in_(("regular", "misconception", "capstone", "reaction"))
            )
        )
    )

    end_ms = max([s.end_ms for s in segments] + [t.t_ms for t in turns], default=0)
    spoken = [(s.start_ms, s.end_ms, s.text) for s in segments]
    metrics = LessonMetrics(
        duration_ms=end_ms,
        words=sum(len(words(text)) for _, _, text in spoken),
        words_per_minute=pace(spoken),
        pause_count=pauses(spoken),
        questions_asked=sum(len(teacher_questions(text)) for _, _, text in spoken),
        wait_times_ms=wait_times(spoken),
        response_times_ms=[q.answered_at_ms - q.asked_at_ms for q in asked if q.answered_at_ms is not None],
        filler_count=sum(len(FILLERS.findall(text.lower())) for _, _, text in spoken),
        time_per_slide=time_per_slide([(t.page, t.t_ms) for t in turns], end_ms),
        segment_wpm=[pace([piece]) for piece in spoken if len(words(piece[2])) >= 5],
    )
    if session.material_id:
        pages: dict[int, str] = {}

        def slide_at(t_ms: int) -> str:
            page = next((t.page for t in reversed(turns) if t.t_ms <= t_ms), 1)
            if page not in pages:
                pages[page] = rag.page_text(db, session.material_id, page)
            return pages[page]

        metrics.reading_share = reading_share([(text, slide_at(start)) for start, _, text in spoken])
    return metrics


def words(text: str) -> list[str]:
    """Lower-case words without punctuation, so "Kuadrat," and "kuadrat" are the same word."""
    return re.findall(r"[^\W_]+", text.lower())


def pace(spoken: list[tuple[int, int, str]]) -> int:
    """Words per minute of speaking time. Silence between pieces is not counted."""
    speaking_ms = sum(end - start for start, end, _ in spoken)
    if speaking_ms <= 0:
        return 0
    return round(sum(len(words(text)) for _, _, text in spoken) / (speaking_ms / 60_000))


def pauses(spoken: list[tuple[int, int, str]]) -> int:
    return sum(1 for gap in _gaps(spoken) if gap >= PAUSE_MS)


def teacher_questions(text: str) -> list[str]:
    """The sentences in one piece of speech that ask the class something."""
    found = []
    for sentence in re.findall(r"[^.!?]+[.!?]?", text):
        sentence = sentence.strip()
        if sentence.endswith("?") or _OPENER.match(sentence.lower()):
            found.append(sentence)
    return found


def closing_question(text: str) -> str | None:
    """The question a piece of speech ends with, or None when its last sentence is not one."""
    sentences = [s.strip() for s in re.findall(r"[^.!?]+[.!?]?", text) if s.strip()]
    if sentences and teacher_questions(sentences[-1]):
        return sentences[-1]
    return None


def wait_times(spoken: list[tuple[int, int, str]]) -> list[int]:
    """The silence after each piece of speech that ends with a question."""
    waits = []
    for (_, end, text), (next_start, _, _) in zip(spoken, spoken[1:]):
        if closing_question(text):
            waits.append(max(next_start - end, 0))
    return waits


def thinking_time_share(waits: list[int]) -> float | None:
    """Share of the teacher's questions followed by at least 3 s of silence."""
    if not waits:
        return None
    return sum(1 for wait in waits if wait >= THINKING_TIME_MS) / len(waits)


def time_per_slide(turns: list[tuple[int, int]], end_ms: int) -> list[dict]:
    """Total time each page was on screen. `turns` is (page, t_ms) in time order."""
    totals: dict[int, int] = {}
    for (page, t_ms), (_, next_ms) in zip(turns, turns[1:] + [(0, end_ms)]):
        totals[page] = totals.get(page, 0) + max(next_ms - t_ms, 0)
    return [{"page": page, "ms": ms} for page, ms in sorted(totals.items())]


def reading_share(pieces: list[tuple[str, str]]) -> float | None:
    """Share of the teacher's words said near word-for-word from the slide on screen.

    `pieces` is (what was said, text of the slide shown at that moment).
    """
    total = read = 0
    for said, slide in pieces:
        said_words, slide_words = words(said), words(slide)
        total += len(said_words)
        on_slide = {tuple(slide_words[i : i + READ_NGRAM]) for i in range(len(slide_words) - READ_NGRAM + 1)}
        covered = [False] * len(said_words)
        for i in range(len(said_words) - READ_NGRAM + 1):
            if tuple(said_words[i : i + READ_NGRAM]) in on_slide:
                covered[i : i + READ_NGRAM] = [True] * READ_NGRAM
        run = 0
        for is_read in covered + [False]:
            if is_read:
                run += 1
                continue
            if run >= READ_RUN:
                read += run
            run = 0
    if total == 0:
        return None
    return round(read / total, 2)


def _gaps(spoken: list[tuple[int, int, str]]) -> list[int]:
    return [next_start - end for (_, end, _), (next_start, _, _) in zip(spoken, spoken[1:])]


def _mean(values: list[int]) -> int | None:
    return round(sum(values) / len(values)) if values else None
