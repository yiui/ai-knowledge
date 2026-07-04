"""延迟初始化 vector_store，避免模块加载时连 Postgres（方便测试 mock）。"""

from langchain_postgres import PGVector

from app.core.config import settings

_vector_store = None


def _get_embedding_model():
    from app.services.embedding_service import _get_embedding_model as _get

    return _get()


def get_vector_store():
    """延迟创建 PGVector —— 避免模块加载时连 Postgres（测试场景需要 mock）。"""
    global _vector_store
    if _vector_store is None:
        _vector_store = PGVector(
            embeddings=_get_embedding_model(),
            collection_name="knowledge",
            connection=settings.DATABASE_URL,
        )
    return _vector_store


# 向后兼容：让 `from app.services.vector_store import vector_store` 仍能工作
# def __getattr__(name):
#     if name == "vector_store":
#         return get_vector_store()
#     raise AttributeError(name)