from langchain_core.documents import Document

from app.core.rerankers import get_rerank_client


def rerank_documents(
    query: str,
    documents: list[Document],
    top_k: int,
) -> list[Document]:
    if not documents:
        return []

    if len(documents) <= top_k:
        return documents

    texts = [doc.page_content for doc in documents]
    ranked = get_rerank_client().rerank(query, texts, top_k)
    return [documents[index] for index, _ in ranked[:top_k]]
