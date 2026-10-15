"""Speech-to-text. The only code that calls a speech-to-text provider.

Provider and model come from .env (STT_PROVIDER, STT_MODEL). Groq and OpenAI
expose the same transcription endpoint, so one request function serves both.
"""

import itertools
import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/audio/transcriptions",
    "openai": "https://api.openai.com/v1/audio/transcriptions",
}
# Used only when the primary provider fails and OPENAI_API_KEY is set.
OPENAI_FALLBACK_MODEL = "whisper-1"
TIMEOUT_S = 30

# Whisper reports, per segment, how likely it is that nobody spoke.
NO_SPEECH_THRESHOLD = 0.6
# Whisper invents these on silence or noise (learned from video subtitles).
HALLUCINATIONS = {
    "terima kasih",
    "terima kasih telah menonton",
    "terima kasih sudah menonton",
    "terima kasih telah menyaksikan",
    "selamat menikmati",
    "sampai jumpa di video selanjutnya",
}

# Whisper copies the style of its prompt, not instructions in it. This shows it punctuated
# classroom speech with question marks, so a teacher's questions are more likely to end in "?".
# It is a nudge, not a guarantee; metrics.py also recognises questions by their opening words.
STYLE_PROMPT = (
    "Baik, anak-anak, kita lanjutkan pelajaran hari ini. Ada yang tahu kenapa hasilnya begitu? "
    "Coba perhatikan contoh berikut. Menurut kalian, berapa nilainya?"
)

# STT_PROVIDER=fake: no key, no network. For building the room without quota.
_fake_lines = itertools.cycle(
    [
        "Baik anak-anak, hari ini kita belajar tentang fungsi kuadrat.",
        "Coba bayangkan bola yang dilempar ke atas, lintasannya melengkung.",
        "Bentuk umumnya adalah a x kuadrat ditambah b x ditambah c.",
        "Ada yang tahu apa yang terjadi kalau nilai a negatif?",
    ]
)


class STTError(RuntimeError):
    pass


def transcribe(wav_bytes: bytes, language: str = "id") -> str:
    """Text of one audio chunk, or "" when the chunk has no speech."""
    provider = settings.stt_provider
    if provider == "fake":
        return next(_fake_lines)
    try:
        return _request(provider, settings.stt_model, wav_bytes, language)
    except httpx.HTTPError as err:
        if provider == "openai" or not settings.openai_api_key:
            raise STTError(f"{provider} transcription failed: {err}") from err
        log.warning("%s transcription failed (%s); falling back to OpenAI", provider, err)
    try:
        return _request("openai", OPENAI_FALLBACK_MODEL, wav_bytes, language)
    except httpx.HTTPError as err:
        raise STTError(f"openai transcription failed: {err}") from err


def _request(provider: str, model: str, wav_bytes: bytes, language: str) -> str:
    if provider not in ENDPOINTS:
        raise STTError(f"Unknown STT_PROVIDER '{provider}' (use groq, openai or fake)")
    key = settings.groq_api_key if provider == "groq" else settings.openai_api_key
    if not key:
        raise STTError(f"No API key for {provider}. Fill it in backend/.env, or set STT_PROVIDER=fake")
    response = httpx.post(
        ENDPOINTS[provider],
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("chunk.wav", wav_bytes, "audio/wav")},
        data={
            "model": model,
            "language": language,
            "response_format": "verbose_json",
            "temperature": "0",
            "prompt": STYLE_PROMPT,
        },
        timeout=TIMEOUT_S,
    )
    response.raise_for_status()
    return clean(response.json())


def clean(payload: dict) -> str:
    """Drop the segments Whisper itself marks as silence, and its stock phrases."""
    segments = payload.get("segments")
    if segments:
        spoken = [s["text"].strip() for s in segments if s.get("no_speech_prob", 0) < NO_SPEECH_THRESHOLD]
        text = " ".join(part for part in spoken if part)
    else:
        text = (payload.get("text") or "").strip()
    if text.lower().strip(" .!?") in HALLUCINATIONS:
        return ""
    # On silence Whisper sometimes repeats its own prompt back.
    if len(text) > 15 and text.lower().strip(" .!?") in STYLE_PROMPT.lower():
        return ""
    return text
