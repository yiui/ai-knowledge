from collections.abc import Iterator

from app.core.config import LLMProvider, settings


def ask_llm(prompt: str, provider: LLMProvider | None = None) -> str:
    match provider or settings.LLM_PROVIDER:
        case "ollama":
            from app.core.ollama import ask_ollama
            print("ask_ollama", prompt)
            return ask_ollama(prompt)
        case "gemini":
            from app.core.gemini import ask_gemini
            print("ask_gemini", prompt)
            return ask_gemini(prompt)
        case other:
            raise ValueError(f"Unsupported LLM provider: {other}")


def stream_llm(prompt: str, provider: LLMProvider | None = None) -> Iterator[str]:
    match provider or settings.LLM_PROVIDER:
        case "ollama":
            from app.core.ollama import stream_ollama

            yield from stream_ollama(prompt)
        case "gemini":
            from app.core.gemini import stream_gemini

            yield from stream_gemini(prompt)
        case other:
            raise ValueError(f"Unsupported LLM provider: {other}")
