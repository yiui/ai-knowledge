from collections.abc import Iterator

from google import genai

from app.core.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.llm_api_key)
    return _client


def ask_gemini(prompt: str) -> str:
    from google.genai import types

    response = _get_client().models.generate_content(
        model=settings.llm_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=settings.LLM_TEMPERATURE or None,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            top_p=settings.LLM_TOP_P or None,
        ),
    )
    return response.text


def stream_gemini(prompt: str) -> Iterator[str]:
    from google.genai import types

    for chunk in _get_client().models.generate_content_stream(
        model=settings.llm_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=settings.LLM_TEMPERATURE or None,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            top_p=settings.LLM_TOP_P or None,
        ),
    ):
        if chunk.text:
            yield chunk.text
