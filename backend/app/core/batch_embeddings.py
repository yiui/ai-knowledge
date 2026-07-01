from langchain_core.embeddings import Embeddings


class BatchEmbeddings(Embeddings):
    """按批次调用底层 embedding，兼容百炼等单次 batch ≤ 20 的 API。"""

    def __init__(self, embeddings: Embeddings, batch_size: int):
        self._embeddings = embeddings
        self._batch_size = max(1, batch_size)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            results.extend(self._embeddings.embed_documents(batch))
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)
