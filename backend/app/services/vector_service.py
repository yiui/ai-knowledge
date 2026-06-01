from app.services.vector_store import vector_store
from sqlalchemy import text
from app.db.session import engine
# 检索相似文档  
def search_similar(query: str, k: int = 4):
    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return retriever.invoke(query)


# 删除文档向量
def delete_document_vectors(document_id: int):
    with engine.begin() as conn:
        conn.execute(
            text("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = :doc_id
            """),
            {
                "doc_id": str(document_id)
            }
        )