from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.services.rerank_service import rerank_documents
from app.services.vector_store import vector_store


def search_similar(
    query: str,
    user_id: int,
    knowledge_base_id: int,
    k: int | None = None,
):
    top_k = k or settings.RERANK_TOP_K
    recall_k = max(top_k, settings.VECTOR_RECALL_K)

    docs = vector_store.similarity_search(
        query,
        k=recall_k,
        filter={
            "user_id": str(user_id),
            "knowledge_base_id": str(knowledge_base_id),
        },
    )

    if not docs:
        return []

    if settings.RERANK_ENABLED and len(docs) > top_k:
        return rerank_documents(query, docs, top_k)

    return docs[:top_k]


def delete_document_vectors(document_id: int, knowledge_base_id: int):
    with engine.begin() as conn:
        conn.execute(
            text("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = :doc_id
                  AND cmetadata->>'knowledge_base_id' = :kb_id
            """),
            {
                "doc_id": str(document_id),
                "kb_id": str(knowledge_base_id),
            },
        )
