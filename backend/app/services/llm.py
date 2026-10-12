"""LLM calls. The only code that calls an LLM provider.

Provider and model come from .env (LLM_PROVIDER, LLM_MODEL). Every caller asks
for JSON that matches a Pydantic class, so a reply is either valid or rejected.
"""

import json
import logging
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
# Used only when the primary provider fails and OPENAI_API_KEY is set.
OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
# Tried in order when LLM_MODEL is busy; they answered on 12 Oct while the newest model returned 503.
GEMINI_FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
TIMEOUT_S = 60
MIN_ATTEMPT_S = 4


class LLMError(RuntimeError):
    pass


def is_fake() -> bool:
    """LLM_PROVIDER=fake: each service returns its own canned value instead of calling this module."""
    return settings.llm_provider == "fake"


def generate_json(prompt: str, schema: type[T], system: str = "", timeout_s: float = TIMEOUT_S) -> T:
    """Ask the model for JSON matching `schema`.

    An invalid reply is sent back once with the validation error. A second
    invalid reply raises LLMError. Temperature is 0 so re-scoring stays stable.
    `timeout_s` is per provider call; pass a short one where the teacher is waiting.
    """
    if is_fake():
        raise LLMError("LLM_PROVIDER=fake: check llm.is_fake() and return a canned value instead")
    shape = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    request = f"{prompt}\n\nBalas hanya dengan satu objek JSON yang mengikuti skema ini:\n{shape}"
    reply = _complete(request, system, timeout_s)
    try:
        return schema.model_validate_json(_strip_fences(reply))
    except ValidationError as err:
        log.warning("LLM reply did not match %s; retrying once", schema.__name__)
        retry = (
            f"{request}\n\nBalasan sebelumnya ditolak:\n{reply}\n\n"
            f"Kesalahan validasi:\n{err}\n\nPerbaiki dan balas hanya dengan JSON yang valid."
        )
    reply = _complete(retry, system, timeout_s)
    try:
        return schema.model_validate_json(_strip_fences(reply))
    except ValidationError as err:
        raise LLMError(f"LLM reply did not match {schema.__name__} after one retry: {err}") from err


def _complete(prompt: str, system: str, timeout_s: float = TIMEOUT_S) -> str:
    """Raw text reply from the configured provider.

    A busy Gemini model (503, 429, timeout) is common on the free tier, so the
    next Gemini model is tried before OpenAI. `timeout_s` covers all Gemini
    attempts together, so a caller with a waiting teacher is never held longer.
    """
    provider = settings.llm_provider
    models = [settings.llm_model]
    if provider == "gemini":
        models += [m for m in GEMINI_FALLBACK_MODELS if m != settings.llm_model]
    deadline = time.monotonic() + timeout_s
    failure: Exception | None = None
    for model in models:
        remaining = deadline - time.monotonic()
        if remaining < MIN_ATTEMPT_S and failure is not None:
            break
        # A hung model may use at most half of what is left, so the next one still gets a turn.
        share = remaining if model == models[-1] else remaining / 2
        try:
            return _call(provider, model, prompt, system, max(share, MIN_ATTEMPT_S))
        except httpx.HTTPError as err:
            failure = err
            log.warning("%s %s failed (%s)", provider, model, _short(err))
    if provider == "openai" or not settings.openai_api_key:
        raise LLMError(f"{provider} call failed: {_short(failure)}") from failure
    log.warning("falling back to OpenAI")
    try:
        return _call("openai", OPENAI_FALLBACK_MODEL, prompt, system, timeout_s)
    except httpx.HTTPError as err:
        raise LLMError(f"gemini failed ({_short(failure)}) and openai failed ({_short(err)})") from err


def _short(err: Exception | None) -> str:
    """Status code or error name, without the long URL httpx appends."""
    if isinstance(err, httpx.HTTPStatusError):
        return f"HTTP {err.response.status_code}"
    return type(err).__name__


def _call(provider: str, model: str, prompt: str, system: str, timeout_s: float) -> str:
    if provider == "gemini":
        return _gemini(model, prompt, system, timeout_s)
    if provider == "openai":
        return _openai(model, prompt, system, timeout_s)
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (use gemini, openai or fake)")


def _gemini(model: str, prompt: str, system: str, timeout_s: float) -> str:
    if not settings.gemini_api_key or not model:
        raise LLMError("Set GEMINI_API_KEY and LLM_MODEL in backend/.env, or LLM_PROVIDER=fake")
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    response = httpx.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": settings.gemini_api_key},
        json=body,
        timeout=timeout_s,
    )
    response.raise_for_status()
    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError) as err:
        raise LLMError(f"Gemini returned no text: {response.text[:300]}") from err
    return "".join(part.get("text", "") for part in parts)


def _openai(model: str, prompt: str, system: str, timeout_s: float) -> str:
    if not settings.openai_api_key or not model:
        raise LLMError("Set OPENAI_API_KEY and LLM_MODEL in backend/.env, or LLM_PROVIDER=fake")
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": prompt})
    response = httpx.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": model, "messages": messages, "temperature": 0, "response_format": {"type": "json_object"}},
        timeout=timeout_s,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _strip_fences(text: str) -> str:
    """Some models wrap JSON in ```json ... ``` even when told not to."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return text.strip()
