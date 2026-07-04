from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.services.keyword_service import invalidate_index, keyword_search
from app.services.rerank_service import rerank_documents


def _get_vector_store():
    """延迟导入 vector_store —— 避免模块加载时连 Postgres（测试场景需要 mock）。"""
    from app.services.vector_store import vector_store
    return vector_store


def search_similar(
    query: str,
    user_id: int,
    knowledge_base_id: int,
    k: int | None = None,
):
    top_k = k or settings.RERANK_TOP_K
    recall_k = max(top_k, settings.VECTOR_RECALL_K)

    docs = _get_vector_store().similarity_search(
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


def _rrf_fusion(
    dense_docs: list,
    sparse_results: list[tuple],
    k: int = 60,
) -> list:
    """Reciprocal Rank Fusion：合并两路排序结果。

    score(d) = 1/(k + rank_dense) + 1/(k + rank_sparse)

    对于只出现在一路中的文档，缺失那路的贡献为 0。
    """
    # 为每篇文档记录两路排名（1-based），用 page_content 作为去重键
    scores: dict[str, dict] = {}

    for rank, doc in enumerate(dense_docs, start=1):
        key = doc.page_content
        scores[key] = {"doc": doc, "dense_rank": rank, "sparse_rank": None}

    for rank, (doc, _bm25_score) in enumerate(sparse_results, start=1):
        key = doc.page_content
        if key in scores:
            scores[key]["sparse_rank"] = rank
        else:
            scores[key] = {"doc": doc, "dense_rank": None, "sparse_rank": rank}

    # 计算 RRF 分数
    fused: list[tuple[float, object]] = []
    for entry in scores.values():
        rrf = 0.0
        if entry["dense_rank"] is not None:
            rrf += 1.0 / (k + entry["dense_rank"])
        if entry["sparse_rank"] is not None:
            rrf += 1.0 / (k + entry["sparse_rank"])
        fused.append((rrf, entry["doc"]))

    # 按 RRF 分数降序
    fused.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in fused]


def search_hybrid(
    query: str,
    user_id: int,
    knowledge_base_id: int,
    k: int | None = None,
):
    """混合检索：向量语义 + BM25 关键词，RRF 融合。"""
    top_k = k or settings.RERANK_TOP_K
    recall_k = max(top_k, settings.VECTOR_RECALL_K)
    keyword_k = max(top_k, settings.KEYWORD_RECALL_K)

    # 1. 向量检索
    dense_docs = _get_vector_store().similarity_search(
        query,
        k=recall_k,
        filter={
            "user_id": str(user_id),
            "knowledge_base_id": str(knowledge_base_id),
        },
    )

    # 2. BM25 关键词检索
    sparse_results = keyword_search(
        query,
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        k=keyword_k,
    )

    # 3. RRF 融合
    fused = _rrf_fusion(dense_docs, sparse_results)

    if not fused:
        return []

    # 4. 可选 Reranker 精排
    if settings.RERANK_ENABLED and len(fused) > top_k:
        return rerank_documents(query, fused, top_k)

    return fused[:top_k]


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
    # 文档删除后使 BM25 索引失效
    invalidate_index(knowledge_base_id)


def upsert_document_vectors(chunks: list, document_id: int, knowledge_base_id: int) -> int:
    """幂等写入文档向量：先删 document_id 对应的旧向量，再插入新向量。

    返回实际写入的 chunk 数。
    必须在 transaction 内：要么全成功、要么全失败，避免半成品。
    """
    with engine.begin() as conn:
        conn.execute(
            text("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = :doc_id
            """),
            {"doc_id": str(document_id)},
        )

    if not chunks:
        return 0

    # PGVector.add_documents 内部会开自己的 session 做 INSERT
    _get_vector_store().add_documents(documents=chunks)
    return len(chunks)
