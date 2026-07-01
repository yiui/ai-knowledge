import httpx

from app.core.config import settings

DASHSCOPE_NATIVE_RERANK_PATH = "/api/v1/services/rerank/text-rerank/text-rerank"
LEGACY_COMPAT_RERANK_URL = "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
LEGACY_NATIVE_RERANK_URL = f"https://dashscope.aliyuncs.com{DASHSCOPE_NATIVE_RERANK_PATH}"


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.rerank_api_key}",
        "Content-Type": "application/json",
    }


def _flat_payload(query: str, documents: list[str], top_n: int) -> dict:
    payload: dict = {
        "model": settings.RERANK_MODEL,
        "query": query,
        "documents": documents,
        "top_n": top_n,
    }
    if settings.RERANK_INSTRUCT.strip():
        payload["instruct"] = settings.RERANK_INSTRUCT.strip()
    return payload


def _nested_payload(query: str, documents: list[str], top_n: int) -> dict:
    parameters: dict = {
        "top_n": top_n,
        "return_documents": False,
    }
    if settings.RERANK_INSTRUCT.strip():
        parameters["instruct"] = settings.RERANK_INSTRUCT.strip()
    return {
        "model": settings.RERANK_MODEL,
        "input": {
            "query": query,
            "documents": documents,
        },
        "parameters": parameters,
    }


def _post_rerank(url: str, payload: dict) -> list[tuple[int, float]]:
    response = httpx.post(
        url,
        headers=_auth_headers(),
        json=payload,
        timeout=settings.RERANK_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return _parse_rerank_results(response.json())


def _rerank_candidate_urls() -> list[str]:
    urls: list[str] = []

    if settings.RERANK_BASE_URL.strip():
        urls.append(settings.RERANK_BASE_URL.strip())

    if host := settings.dashscope_workspace_host:
        urls.append(f"{host}/compatible-api/v1/reranks")
        urls.append(f"{host}{DASHSCOPE_NATIVE_RERANK_PATH}")

    urls.extend([LEGACY_COMPAT_RERANK_URL, LEGACY_NATIVE_RERANK_URL])

    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


def _rerank_with_fallback(
    query: str,
    documents: list[str],
    top_n: int,
    payloads: list[dict],
) -> list[tuple[int, float]]:
    last_error: httpx.HTTPStatusError | None = None

    for url in _rerank_candidate_urls():
        for payload in payloads:
            try:
                return _post_rerank(url, payload)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in {404, 405}:
                    continue
                raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("No rerank endpoint configured")


class OpenAICompatRerankClient:
    """OpenAI 兼容 rerank（百炼 qwen3-rerank 等，扁平 JSON）。"""

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[tuple[int, float]]:
        return _rerank_with_fallback(
            query,
            documents,
            top_n,
            payloads=[_flat_payload(query, documents, top_n)],
        )


class DashScopeRerankClient:
    """DashScope 原生 rerank（gte-rerank-v2 等，嵌套 input/parameters）。"""

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[tuple[int, float]]:
        return _rerank_with_fallback(
            query,
            documents,
            top_n,
            payloads=[
                _nested_payload(query, documents, top_n),
                _flat_payload(query, documents, top_n),
            ],
        )


class OllamaRerankClient:
    """Ollama /api/rerank（需 Ollama 新版本及 rerank 模型）。"""

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[tuple[int, float]]:
        base = settings.rerank_base_url_ollama.rstrip("/")
        payload: dict = {
            "model": settings.RERANK_MODEL,
            "query": query,
            "documents": documents,
        }
        if top_n > 0:
            payload["top_n"] = top_n

        response = httpx.post(
            f"{base}/api/rerank",
            json=payload,
            timeout=settings.RERANK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return _parse_rerank_results(response.json())


def _parse_rerank_results(data: dict) -> list[tuple[int, float]]:
    if "results" in data:
        results = data["results"]
    elif "output" in data and isinstance(data["output"], dict):
        results = data["output"].get("results", [])
    else:
        raise ValueError(f"Unexpected rerank response: {data}")

    ranked: list[tuple[int, float]] = []
    for item in results:
        index = int(item["index"])
        score = float(item.get("relevance_score", item.get("score", 0.0)))
        ranked.append((index, score))
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked
