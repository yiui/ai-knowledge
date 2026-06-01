from collections.abc import Iterator

from google import genai

from app.core.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def ask_gemini(prompt: str) -> str:
    response = _get_client().models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )
    return response.text


def stream_gemini(prompt: str) -> Iterator[str]:
    for chunk in _get_client().models.generate_content_stream(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    ):
        if chunk.text:
            yield chunk.text
