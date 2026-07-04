"""延迟初始化 vector_store，避免模块加载时连 Postgres（方便测试 mock）。"""

import threading

from langchain_postgres import PGVector

from app.core.config import settings
from app.db.session import engine

_vector_store = None
_lock = threading.Lock()


def _get_embedding_model():
    from app.services.embedding_service import _get_embedding_model as _get

    return _get()


def get_vector_store():
    """延迟创建 PGVector —— 避免模块加载时连 Postgres（测试场景需要 mock）。

    线程安全：用锁保护懒加载，防止多个 BackgroundTask 并发创建 PGVector 实例
    导致 langchain-postgres 内部模块级 MetaData 表重复注册。
    """
    global _vector_store
    if _vector_store is None:
        with _lock:
            if _vector_store is None:
                _vector_store = PGVector(
                    embeddings=_get_embedding_model(),
                    collection_name="knowledge",
                    connection=engine,
                )
    return _vector_store


# 向后兼容：让 `from app.services.vector_store import vector_store` 仍能工作
# def __getattr__(name):
#     if name == "vector_store":
#         return get_vector_store()
#     raise AttributeError(name)