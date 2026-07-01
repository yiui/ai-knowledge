from app.core.config import settings
from app.core.rerankers.base import RerankClient
from app.core.rerankers.http_clients import (
    DashScopeRerankClient,
    OllamaRerankClient,
    OpenAICompatRerankClient,
)

_rerank_client: RerankClient | None = None


def create_rerank_client() -> RerankClient:
    match settings.RERANK_PROVIDER:
        case "openai_compat":
            return OpenAICompatRerankClient()
        case "dashscope":
            return DashScopeRerankClient()
        case "ollama":
            return OllamaRerankClient()
        case other:
            raise ValueError(f"Unsupported rerank provider: {other}")


def get_rerank_client() -> RerankClient:
    global _rerank_client
    if _rerank_client is None:
        _rerank_client = create_rerank_client()
    return _rerank_client
