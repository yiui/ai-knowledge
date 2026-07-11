import json
import logging
from collections.abc import Iterator

import httpx

from app.core.config import settings

log = logging.getLogger("deepseek")
_client: httpx.Client | None = None


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        base_url = settings.llm_base_url.rstrip("/")
        _client = httpx.Client(base_url=base_url, timeout=120.0)
    return _client


def _build_payload(prompt: str, *, stream: bool) -> dict:
    payload: dict = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "top_p": settings.LLM_TOP_P,
    }
    return payload


def ask_deepseek(prompt: str) -> str:
    response = _get_client().post(
        "/chat/completions",
        headers=_headers(),
        json=_build_payload(prompt, stream=False),
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def stream_deepseek(prompt: str) -> Iterator[str]:
    with _get_client().stream(
        "POST",
        "/chat/completions",
        headers=_headers(),
        json=_build_payload(prompt, stream=True),
    ) as response:
        log.info("stream request url=%s/chat/completions status=%s",
                 _get_client().base_url, response.status_code)
        response.raise_for_status()
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                log.warning("skip unparseable line: %s", line[:200])
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            if text := delta.get("content"):
                yield text
