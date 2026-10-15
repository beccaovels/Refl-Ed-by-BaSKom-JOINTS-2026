"""Keeps the report honest and kind.

Two checks run on everything the LLM writes before a teacher sees it:
a quote must really be the teacher's own words (said in the transcript, or
written in a worked example they confirmed), and the wording must follow the
feedback rules in docs/delivery-grading.md.
"""

import re

from app.models import TranscriptSegment
from app.services.metrics import words

MIN_QUOTE_WORDS = 3  # "ya" or "oke" would match almost any lesson
_STEP_NUMBER = re.compile(r"^(langkah\s+)?\d+\s*[.):]\s*", re.IGNORECASE)

BANNED = ("kurang", "lemah", "seharusnya", "lacking", "poor", "weak", "should")
# "kurang dari" (less than) and "kurang lebih" (roughly) are ordinary words in a lesson, not a judgement.
ALLOWED_PHRASES = re.compile(r"\b(kurang dari|kurang lebih|lebih kurang)\b")
_BANNED = re.compile(r"\b(" + "|".join(BANNED) + r")\b")

# No emotion labels: the report never says how the teacher seemed to feel.
EMOTIONS = (
    "gugup", "grogi", "cemas", "tegang", "takut", "ragu-ragu", "bosan", "murung", "sedih", "marah", "kesal",
    "ceria", "gembira", "bahagia", "percaya diri", "tidak percaya diri", "lesu", "malas",
    "nervous", "anxious", "bored", "sad", "angry", "happy", "cheerful", "confident", "unconfident", "lazy",
)  # fmt: skip
_EMOTIONS = re.compile(r"\b(" + "|".join(EMOTIONS) + r")\b")


def find_quote(quote: str | None, segments: list[TranscriptSegment]) -> int | None:
    """When the teacher said `quote`, as ms from the start of the lesson, or None if they never did.

    Case and punctuation are ignored. A quote may run across two audio pieces.
    """
    wanted = words(quote or "")
    if len(wanted) < MIN_QUOTE_WORDS:
        return None
    spoken: list[str] = []
    said_at: list[int] = []
    for segment in segments:
        for word in words(segment.text):
            spoken.append(word)
            said_at.append(segment.start_ms)
    for i in range(len(spoken) - len(wanted) + 1):
        if spoken[i : i + len(wanted)] == wanted:
            return said_at[i]
    return None


def find_written(quote: str | None, written: dict[int, list[str]]) -> int | None:
    """The page on which the teacher wrote `quote`, or None if they never did.

    `written` maps the page of a worked example to its lines, and holds only
    examples the teacher confirmed: until then the text is our reading of a
    photo, not their words. Matched word for word, like `find_quote`.
    """
    wanted = words(unnumbered(quote))
    if len(wanted) < MIN_QUOTE_WORDS:
        return None
    for page, lines in written.items():
        on_page = [word for line in lines for word in words(line)]
        if any(on_page[i : i + len(wanted)] == wanted for i in range(len(on_page) - len(wanted) + 1)):
            return page
    return None


def unnumbered(quote: str | None) -> str:
    """A written line without the step number in front: the model is shown "2. n(A) = 6" and often quotes it that way."""
    return _STEP_NUMBER.sub("", (quote or "").strip())


def banned_words(text: str | None) -> list[str]:
    """The banned words in a text the teacher will read. Empty means the wording is fine."""
    cleaned = ALLOWED_PHRASES.sub(" ", (text or "").lower())
    return sorted(set(_BANNED.findall(cleaned)))


def emotion_words(text: str | None) -> list[str]:
    """Words that label how the teacher felt. Feedback describes the lesson, never a mood."""
    return sorted(set(_EMOTIONS.findall((text or "").lower())))


def unkind(text: str | None) -> bool:
    """True when a feedback text breaks a wording rule and must not reach the teacher."""
    return bool(banned_words(text) or emotion_words(text))
