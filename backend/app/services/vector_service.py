from sqlalchemy import text

from app.db.session import engine
from app.services.vector_store import vector_store


def search_similar(query: str, user_id: int, knowledge_base_id: int, k: int = 4):
    return vector_store.similarity_search(
        query,
        k=k,
        filter={
            "user_id": str(user_id),
            "knowledge_base_id": str(knowledge_base_id),
        },
    )


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
