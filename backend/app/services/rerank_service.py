from langchain_core.documents import Document

from app.core.config import settings

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(settings.RERANK_MODEL)
    return _reranker


def rerank_documents(
    query: str,
    documents: list[Document],
    top_k: int,
) -> list[Document]:
    if not documents:
        return []

    if len(documents) <= top_k:
        return documents

    reranker = _get_reranker()
    pairs = [(query, doc.page_content) for doc in documents]
    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(documents, scores, strict=True),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    return [doc for doc, _ in ranked[:top_k]]
