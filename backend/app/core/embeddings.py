from langchain_core.embeddings import Embeddings

from app.core.batch_embeddings import BatchEmbeddings
from app.core.config import settings


def create_embeddings() -> Embeddings:
    match settings.EMBEDDING_PROVIDER:
        case "openai_compat":
            from langchain_openai import OpenAIEmbeddings

            kwargs: dict = {
                "model": settings.EMBEDDING_MODEL,
                "openai_api_key": settings.EMBEDDING_API_KEY,
                "openai_api_base": settings.EMBEDDING_BASE_URL,
                "check_embedding_ctx_length": False,
            }
            if settings.EMBEDDING_DIMENSIONS > 0:
                kwargs["dimensions"] = settings.EMBEDDING_DIMENSIONS
            base = OpenAIEmbeddings(**kwargs)
            return BatchEmbeddings(base, settings.EMBEDDING_BATCH_SIZE)
        case "ollama":
            from langchain_ollama import OllamaEmbeddings

            base = OllamaEmbeddings(
                model=settings.EMBEDDING_MODEL,
                base_url=settings.EMBEDDING_BASE_URL,
            )
            return BatchEmbeddings(base, settings.EMBEDDING_BATCH_SIZE)
        case other:
            raise ValueError(f"Unsupported embedding provider: {other}")
