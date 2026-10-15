"""LLM calls. The only code that calls an LLM provider.

Provider and model come from .env (LLM_PROVIDER, LLM_MODEL). Every caller asks
for JSON that matches a Pydantic class, so a reply is either valid or rejected.
"""

import base64
import json
import logging
import time
from collections.abc import Sequence
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
Image = tuple[bytes, str]  # the file's bytes and its type, e.g. "image/jpeg"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
# Used only when the primary provider fails and OPENAI_API_KEY is set.
OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
# Tried in order when LLM_MODEL is busy; they answered on 12 Oct while the newest model returned 503.
GEMINI_FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
TIMEOUT_S = 60
MIN_ATTEMPT_S = 4
# After a failure a model is not tried again for this long, so a busy model
# does not cost several seconds on every question while the teacher waits.
REST_S = 120
_resting_until: dict[str, float] = {}


class LLMError(RuntimeError):
    pass


def is_fake() -> bool:
    """LLM_PROVIDER=fake: each service returns its own canned value instead of calling this module."""
    return settings.llm_provider == "fake"


def generate_json(
    prompt: str,
    schema: type[T],
    system: str = "",
    timeout_s: float = TIMEOUT_S,
    images: Sequence[Image] = (),
    model: str | None = None,
) -> T:
    """Ask the model for JSON matching `schema`.

    An invalid reply is sent back once with the validation error. A second
    invalid reply raises LLMError. Temperature is 0 so re-scoring stays stable.
    `timeout_s` is per provider call; pass a short one where the teacher is waiting.
    `images` are shown to the model with the prompt, e.g. a photo of handwriting.
    `model` is tried before LLM_MODEL, for a job one Gemini model does better than the others.
    """
    if is_fake():
        raise LLMError("LLM_PROVIDER=fake: check llm.is_fake() and return a canned value instead")
    shape = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    request = f"{prompt}\n\nBalas hanya dengan satu objek JSON yang mengikuti skema ini:\n{shape}"
    reply = _complete(request, system, timeout_s, images, model)
    try:
        return schema.model_validate_json(_strip_fences(reply))
    except ValidationError as err:
        log.warning("LLM reply did not match %s; retrying once", schema.__name__)
        retry = (
            f"{request}\n\nBalasan sebelumnya ditolak:\n{reply}\n\n"
            f"Kesalahan validasi:\n{err}\n\nPerbaiki dan balas hanya dengan JSON yang valid."
        )
    reply = _complete(retry, system, timeout_s, images, model)
    try:
        return schema.model_validate_json(_strip_fences(reply))
    except ValidationError as err:
        raise LLMError(f"LLM reply did not match {schema.__name__} after one retry: {err}") from err


def _complete(
    prompt: str, system: str, timeout_s: float = TIMEOUT_S, images: Sequence[Image] = (), first: str | None = None
) -> str:
    """Raw text reply from the configured provider.

    A busy Gemini model (503, 429, timeout) is common on the free tier, so the
    next Gemini model is tried before OpenAI. `timeout_s` covers all Gemini
    attempts together, so a caller with a waiting teacher is never held longer.
    `first` names a Gemini model to try before the usual ones.
    """
    provider = settings.llm_provider
    models = [settings.llm_model]
    if provider == "gemini":
        # dict.fromkeys keeps the order and drops a model named twice
        models = [m for m in dict.fromkeys([first, settings.llm_model, *GEMINI_FALLBACK_MODELS]) if m is not None]
    deadline = time.monotonic() + timeout_s
    failure: Exception | None = None
    # A model that just failed is skipped for a while, unless every model is resting.
    rested = [m for m in models if _resting_until.get(m, 0) <= time.monotonic()]
    for model in rested or models:
        remaining = deadline - time.monotonic()
        if remaining < MIN_ATTEMPT_S and failure is not None:
            break
        # A hung model may use at most half of what is left, so the next one still gets a turn.
        share = remaining if model == models[-1] else remaining / 2
        try:
            return _call(provider, model, prompt, system, max(share, MIN_ATTEMPT_S), images)
        except httpx.HTTPError as err:
            failure = err
            _resting_until[model] = time.monotonic() + REST_S
            log.warning("%s %s failed (%s); skipping it for %d s", provider, model, _short(err), REST_S)
    if provider == "openai" or not settings.openai_api_key:
        raise LLMError(f"{provider} call failed: {_short(failure)}") from failure
    log.warning("falling back to OpenAI")
    try:
        return _call("openai", OPENAI_FALLBACK_MODEL, prompt, system, timeout_s, images)
    except httpx.HTTPError as err:
        raise LLMError(f"gemini failed ({_short(failure)}) and openai failed ({_short(err)})") from err


def _short(err: Exception | None) -> str:
    """Status code or error name, without the long URL httpx appends."""
    if isinstance(err, httpx.HTTPStatusError):
        return f"HTTP {err.response.status_code}"
    return type(err).__name__


def _call(provider: str, model: str, prompt: str, system: str, timeout_s: float, images: Sequence[Image] = ()) -> str:
    if provider == "gemini":
        return _gemini(model, prompt, system, timeout_s, images)
    if provider == "openai":
        return _openai(model, prompt, system, timeout_s, images)
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}' (use gemini, openai or fake)")


def _gemini(model: str, prompt: str, system: str, timeout_s: float, images: Sequence[Image] = ()) -> str:
    if not settings.gemini_api_key or not model:
        raise LLMError("Set GEMINI_API_KEY and LLM_MODEL in backend/.env, or LLM_PROVIDER=fake")
    shown = [{"inline_data": {"mime_type": kind, "data": _base64(data)}} for data, kind in images]
    body: dict = {
        "contents": [{"role": "user", "parts": [*shown, {"text": prompt}]}],
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


def _openai(model: str, prompt: str, system: str, timeout_s: float, images: Sequence[Image] = ()) -> str:
    if not settings.openai_api_key or not model:
        raise LLMError("Set OPENAI_API_KEY and LLM_MODEL in backend/.env, or LLM_PROVIDER=fake")
    messages: list[dict] = [{"role": "system", "content": system}] if system else []
    shown = [{"type": "image_url", "image_url": {"url": f"data:{kind};base64,{_base64(data)}"}} for data, kind in images]
    messages.append({"role": "user", "content": [*shown, {"type": "text", "text": prompt}] if shown else prompt})
    response = httpx.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": model, "messages": messages, "temperature": 0, "response_format": {"type": "json_object"}},
        timeout=timeout_s,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _strip_fences(text: str) -> str:
    """Some models wrap JSON in ```json ... ``` even when told not to."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return text.strip()
