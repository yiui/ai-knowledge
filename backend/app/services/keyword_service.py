"""BM25 关键词检索服务。

使用 jieba 中文分词 + rank_bm25 实现关键词检索。
索引按知识库维度懒加载，文档变更后自动失效。
"""

import jieba
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


class _KeywordIndex:
    """单个知识库的 BM25 索引。"""

    def __init__(self, chunks: list[Document]):
        self.chunks = chunks
        tokenized = [_tokenize(doc.page_content) for doc in chunks]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        if self.bm25 is None:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        # 按分数降序取 top-k
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)
        return [(self.chunks[i], float(score)) for i, score in indexed[:k] if score > 0]


# 知识库 ID → 索引
_indexes: dict[int, _KeywordIndex] = {}


def _tokenize(text: str) -> list[str]:
    """对文本做中文分词，同时保留字母数字 token。"""
    tokens: list[str] = []
    for token in jieba.cut(text):
        token = token.strip()
        if token:
            tokens.append(token)
    return tokens


def _load_chunks(knowledge_base_id: int, user_id: int) -> list[Document]:
    """从 PGVector 读取指定知识库的全部 chunk。"""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT document, cmetadata
                FROM langchain_pg_embedding
                WHERE cmetadata->>'knowledge_base_id' = :kb_id
                  AND cmetadata->>'user_id' = :uid
            """),
            {"kb_id": str(knowledge_base_id), "uid": str(user_id)},
        ).fetchall()

    docs: list[Document] = []
    for row in rows:
        docs.append(Document(page_content=row[0], metadata=row[1] or {}))
    return docs


def build_index(knowledge_base_id: int, user_id: int) -> _KeywordIndex:
    """构建（或重建）指定知识库的 BM25 索引。"""
    chunks = _load_chunks(knowledge_base_id, user_id)
    index = _KeywordIndex(chunks)
    _indexes[knowledge_base_id] = index
    return index


def invalidate_index(knowledge_base_id: int) -> None:
    """使指定知识库的索引失效（文档变更后调用）。"""
    _indexes.pop(knowledge_base_id, None)


def keyword_search(
    query: str,
    knowledge_base_id: int,
    user_id: int,
    k: int | None = None,
) -> list[tuple[Document, float]]:
    """对指定知识库执行 BM25 关键词检索。

    索引不存在时自动构建。
    返回 (Document, bm25_score) 列表，按分数降序。
    """
    top_k = k or settings.KEYWORD_RECALL_K

    index = _indexes.get(knowledge_base_id)
    if index is None:
        index = build_index(knowledge_base_id, user_id)

    return index.search(query, top_k)
