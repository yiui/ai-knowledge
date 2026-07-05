import json
from collections.abc import Iterator

import httpx

from app.core.config import settings

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url=settings.llm_base_url, timeout=120.0)
    return _client


def _build_payload(prompt: str, *, stream: bool) -> dict:
    return {
        "model": settings.llm_model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": settings.LLM_TEMPERATURE,
            "num_predict": settings.LLM_MAX_TOKENS,
            "top_p": settings.LLM_TOP_P,
        },
    }


def ask_ollama(prompt: str) -> str:
    response = _get_client().post(
        "/api/generate",
        json=_build_payload(prompt, stream=False),
    )
    response.raise_for_status()
    return response.json()["response"]


def stream_ollama(prompt: str) -> Iterator[str]:
    with _get_client().stream(
        "POST",
        "/api/generate",
        json=_build_payload(prompt, stream=True),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if text := chunk.get("response"):
                yield text
