from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.services.keyword_service import invalidate_index, keyword_search
from app.services.rerank_service import rerank_documents


def _get_vector_store():
    from app.services.vector_store import get_vector_store
    return get_vector_store()


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


def get_adjacent_chunks(
    docs: list,
    knowledge_base_id: int,
    user_id: int,
) -> list:
    """获取已召回 chunk 的相邻 chunk（同一文档的 chunk_index ± 1）。

    用于解决结构化知识点被分块切断的问题（如"产品三环靶"跨 3 个 chunk）。
    """
    from langchain_core.documents import Document as LCDocument

    # 收集需要扩展的 (document_id, chunk_index) 对
    targets: set[tuple[str, int]] = set()
    for doc in docs:
        doc_id = doc.metadata.get("document_id")
        idx = doc.metadata.get("chunk_index")
        if doc_id is not None and idx is not None:
            targets.add((str(doc_id), int(idx)))

    if not targets:
        return []

    # 为每个命中 chunk 计算 ±1 的相邻索引，排除已命中的索引
    wanted: dict[str, set[int]] = {}  # document_id → set of chunk_index
    already: set[tuple[str, int]] = set()
    for doc_id, idx in targets:
        already.add((doc_id, idx))
        wanted.setdefault(doc_id, set()).update([idx - 1, idx + 1])

    # 移除负数索引和已存在的索引
    for doc_id in wanted:
        wanted[doc_id] = {i for i in wanted[doc_id] if i >= 0 and (doc_id, i) not in already}

    # 展平为 (document_id, chunk_index) 列表
    flat = [(doc_id, idx) for doc_id, indices in wanted.items() for idx in indices]
    if not flat:
        return []

    # 批量查询 PGVector
    from app.db.session import engine
    from sqlalchemy import text

    with engine.connect() as conn:
        # 构建 WHERE 条件：(cmetadata->>'document_id', cmetadata->>'chunk_index') IN (...)
        values_clause = ", ".join([f"('{did}', '{idx}')" for did, idx in flat])
        result = conn.execute(
            text(f"""
                SELECT document, cmetadata
                FROM langchain_pg_embedding
                WHERE cmetadata->>'knowledge_base_id' = :kb_id
                  AND cmetadata->>'user_id' = :uid
                  AND (cmetadata->>'document_id', cmetadata->>'chunk_index') IN ({values_clause})
            """),
            {"kb_id": str(knowledge_base_id), "uid": str(user_id)},
        )
        rows = result.fetchall()

    adjacent: list[LCDocument] = []
    for row in rows:
        doc = LCDocument(page_content=row[0], metadata=row[1] or {})
        adjacent.append(doc)

    return adjacent


def get_document_chunks(
    document_id: int,
    knowledge_base_id: int,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """返回文档的分块，按 chunk_index 排序，支持分页。用于预览。"""
    from app.db.session import engine
    from sqlalchemy import text

    params = {
        "doc_id": str(document_id),
        "kb_id": str(knowledge_base_id),
        "uid": str(user_id),
    }

    with engine.connect() as conn:
        total = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = :doc_id
                  AND cmetadata->>'knowledge_base_id' = :kb_id
                  AND cmetadata->>'user_id' = :uid
            """),
            params,
        ).scalar()

        offset = (page - 1) * page_size
        rows = conn.execute(
            text("""
                SELECT document, cmetadata
                FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = :doc_id
                  AND cmetadata->>'knowledge_base_id' = :kb_id
                  AND cmetadata->>'user_id' = :uid
                ORDER BY (cmetadata->>'chunk_index')::int ASC
                LIMIT :limit OFFSET :offset
            """),
            {**params, "limit": page_size, "offset": offset},
        ).fetchall()

    items = [
        {
            "chunk_index": (row[1] or {}).get("chunk_index", offset + i),
            "chunk_total": (row[1] or {}).get("chunk_total", total),
            "content": row[0],
            "content_length": len(row[0]) if row[0] else 0,
        }
        for i, row in enumerate(rows)
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def delete_document_vectors(document_id: int, knowledge_base_id: int):
    # 确保 PGVector 表已创建（首次调用时建表）
    _get_vector_store()
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


def _sanitize_text(text: str) -> str:
    """移除 PostgreSQL 不能存储的字符（NUL 等）。"""
    if not text:
        return text
    return text.replace("\x00", "")


def upsert_document_vectors(chunks: list, document_id: int, knowledge_base_id: int) -> int:
    """幂等写入文档向量：先删 document_id 对应的旧向量，再插入新向量。

    返回实际写入的 chunk 数。
    """
    if not chunks:
        return 0

    # 最终防线：确保 chunk 文本和 metadata 不含 NUL 字符
    for chunk in chunks:
        chunk.page_content = _sanitize_text(chunk.page_content)
        if chunk.metadata:
            for k, v in chunk.metadata.items():
                if isinstance(v, str):
                    chunk.metadata[k] = _sanitize_text(v)

    # 先触发 PGVector 初始化（首次调用会建 langchain_pg_embedding 表），
    # 否则下面的 DELETE 会因为表不存在而报错。
    vs = _get_vector_store()

    with engine.begin() as conn:
        conn.execute(
            text("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = :doc_id
            """),
            {"doc_id": str(document_id)},
        )

    # PGVector.add_documents 内部会开自己的 session 做 INSERT
    vs.add_documents(documents=chunks)
    return len(chunks)
