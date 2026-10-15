"""Calls each AI provider once with the keys in backend/.env and prints what came back.

Run from the backend folder:
    python ../ml/eval/check_providers.py                 LLM only
    python ../ml/eval/check_providers.py path/to/clip.wav   LLM and speech-to-text
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import httpx  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services import llm, stt  # noqa: E402


class StudentQuestion(BaseModel):
    question: str


def check_llm() -> None:
    print(f"LLM  provider={settings.llm_provider} model={settings.llm_model or '(not set)'}")
    if settings.llm_provider == "gemini" and not settings.llm_model:
        listing = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": settings.gemini_api_key},
            params={"pageSize": 200},
            timeout=30,
        )
        listing.raise_for_status()
        names = [m["name"].removeprefix("models/") for m in listing.json()["models"]]
        print("     Set LLM_MODEL in .env to one of:", ", ".join(n for n in names if "flash" in n))
        return
    started = time.perf_counter()
    reply = llm.generate_json(
        "Kamu murid kelas X. Guru baru saja menjelaskan bahwa grafik fungsi kuadrat berbentuk parabola. "
        "Tulis satu pertanyaan singkat yang mungkin kamu ajukan.",
        StudentQuestion,
    )
    print(f"     {time.perf_counter() - started:.1f} s  →  {reply.question}")


def check_stt(path: Path) -> None:
    print(f"STT  provider={settings.stt_provider} model={settings.stt_model}")
    started = time.perf_counter()
    text = stt.transcribe(path.read_bytes())
    print(f"     {time.perf_counter() - started:.1f} s  →  {text or '(no speech)'}")


if __name__ == "__main__":
    check_llm()
    if len(sys.argv) > 1:
        check_stt(Path(sys.argv[1]))
