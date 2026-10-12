"""Keeps the report honest and kind.

Two checks run on everything the LLM writes before a teacher sees it:
a quote must really be in the transcript, and the wording must follow the
feedback rules in docs/delivery-grading.md.
"""

import re

from app.models import TranscriptSegment
from app.services.metrics import words

MIN_QUOTE_WORDS = 3  # "ya" or "oke" would match almost any lesson

BANNED = ("kurang", "lemah", "seharusnya", "lacking", "poor", "weak", "should")
# "kurang dari" (less than) and "kurang lebih" (roughly) are ordinary words in a lesson, not a judgement.
ALLOWED_PHRASES = re.compile(r"\b(kurang dari|kurang lebih|lebih kurang)\b")
_BANNED = re.compile(r"\b(" + "|".join(BANNED) + r")\b")


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


def banned_words(text: str | None) -> list[str]:
    """The banned words in a text the teacher will read. Empty means the wording is fine."""
    cleaned = ALLOWED_PHRASES.sub(" ", (text or "").lower())
    return sorted(set(_BANNED.findall(cleaned)))
