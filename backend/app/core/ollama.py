import json
from collections.abc import Iterator

import httpx

from app.core.config import settings

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url=settings.OLLAMA_BASE_URL, timeout=120.0)
    return _client


def ask_ollama(prompt: str) -> str:
    response = _get_client().post(
        "/api/generate",
        json={
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        },
    )
    response.raise_for_status()
    return response.json()["response"]


def stream_ollama(prompt: str) -> Iterator[str]:
    with _get_client().stream(
        "POST",
        "/api/generate",
        json={
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True,
        },
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if text := chunk.get("response"):
                yield text
