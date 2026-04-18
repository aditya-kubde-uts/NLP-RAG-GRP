"""Azure OpenAI routing helpers for embeddings and completions."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Iterable
from typing import Any

import tiktoken
from openai import AzureOpenAI

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)

_settings = get_settings()
_client = AzureOpenAI(
    api_key=_settings.azure_openai_api_key,
    api_version=_settings.azure_openai_api_version,
    azure_endpoint=_settings.azure_openai_endpoint,
)

MAX_RETRIES = 3


def _with_retries(fn_name: str, call):
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call()
        except Exception as exc:  # pragma: no cover - network behavior
            last_exc = exc
            if attempt >= MAX_RETRIES:
                break
            delay = 2 ** (attempt - 1)
            log.warning("llm_retry", fn=fn_name, attempt=attempt, delay_s=delay, error=str(exc))
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def count_tokens(text: str, model_hint: str = "gpt-4") -> int:
    """Approximate token count (fallback heuristic if model encoding unknown)."""
    try:
        enc = tiktoken.encoding_for_model(model_hint)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def get_embedding(texts: list[str]) -> list[list[float]]:
    """Return embedding vectors for a batch of texts."""
    if not texts:
        return []

    def _call():
        return _client.embeddings.create(model=_settings.azure_embedding_deployment_name, input=texts)

    res = _with_retries("get_embedding", _call)
    vectors: list[list[float]] = []
    for item in res.data:
        vectors.append(list(item.embedding))
    return vectors


def get_completion(prompt: str, system_prompt: str = "") -> str:
    """Generate a single-shot completion."""
    messages: list[dict[str, str]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    def _call():
        return _client.chat.completions.create(
            model=_settings.azure_llm_deployment_name,
            messages=messages,
            temperature=0.2,
        )

    res = _with_retries("get_completion", _call)
    msg = (res.choices[0].message.content or "").strip()
    return msg


def get_completion_streaming(prompt: str, system_prompt: str = "") -> Iterable[str]:
    """Yield completion chunks (for SSE endpoints)."""
    messages: list[dict[str, str]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    def _call():
        return _client.chat.completions.create(
            model=_settings.azure_llm_deployment_name,
            messages=messages,
            temperature=0.2,
            stream=True,
        )

    stream = _with_retries("get_completion_streaming", _call)
    for chunk in stream:  # pragma: no branch
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


async def aget_embedding(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(get_embedding, texts)


async def aget_completion(prompt: str, system_prompt: str = "") -> str:
    return await asyncio.to_thread(get_completion, prompt, system_prompt)


async def aget_completion_streaming(
    prompt: str, system_prompt: str = ""
) -> AsyncGenerator[str, None]:
    chunks = await asyncio.to_thread(lambda: list(get_completion_streaming(prompt, system_prompt)))
    for chunk in chunks:
        yield chunk


def usage_tokens_from_response(response: Any) -> dict[str, int]:
    """Best-effort token usage extraction for cost tracking."""
    usage = getattr(response, "usage", None)
    if not usage:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }

