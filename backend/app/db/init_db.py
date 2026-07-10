"""运行时数据库初始化 & 幂等迁移。

- 老用户：`Base.metadata.create_all` 不会给已存在的表加列；
  `_migrate_documents_status_columns` 检测并 ALTER 已有 documents 表。
- 真正的 schema 版本演进建议后续接 Alembic（pyproject.toml 已含 alembic 依赖）。
"""
from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.session import engine

# 导入模型（关键，不然不会建表）
from app.models import conversation, document, knowledge_base, message, user  # noqa: F401


def _migrate_users_table() -> None:
    """确保 users 表结构最新（幂等 ALTER，绝不 DROP）。"""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    # 如果缺核心列，说明是极老的结构，打印警告让人工处理（不再自动 DROP）
    missing = {"username", "password_hash"} - columns
    if missing:
        print(
            f"[init_db] WARNING: users table missing columns {missing}, "
            f"please migrate manually"
        )


def _migrate_documents_table() -> None:
    """重建老结构的 documents 表（仅在缺核心字段时）。"""
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("documents")}
    if "knowledge_base_id" in columns:
        return

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))
        if "langchain_pg_embedding" in inspector.get_table_names():
            conn.execute(text("DELETE FROM langchain_pg_embedding"))


def _migrate_documents_status_columns() -> None:
    """向已存在的 documents 表加 status / error_message / vector_count / updated_at 字段。

    幂等：每次启动都执行，缺啥补啥。
    老数据回填：status='ready'（这些文档历史上已成功入向量库），vector_count=0。
    """
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("documents")}
    with engine.begin() as conn:
        if "status" not in existing:
            conn.execute(text(
                "ALTER TABLE documents "
                "ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'pending'"
            ))
            # 老数据视为已就绪（历史上入过向量库）
            conn.execute(text(
                "UPDATE documents SET status = 'ready' "
                "WHERE status = 'pending' AND created_at < NOW() - INTERVAL '5 minute'"
            ))
        if "error_message" not in existing:
            conn.execute(text(
                "ALTER TABLE documents ADD COLUMN error_message TEXT"
            ))
        if "vector_count" not in existing:
            conn.execute(text(
                "ALTER TABLE documents "
                "ADD COLUMN vector_count INTEGER NOT NULL DEFAULT 0"
            ))
        if "updated_at" not in existing:
            conn.execute(text(
                "ALTER TABLE documents "
                "ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT NOW()"
            ))
        # status 索引（若缺失则建）
        idx_names = {idx["name"] for idx in inspector.get_indexes("documents")}
        if "ix_documents_status" not in idx_names:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status)"
            ))


def _migrate_messages_sources_column() -> None:
    """向 messages 表加 sources JSONB 列（存 RAG 来源元数据）。"""
    inspector = inspect(engine)
    if "messages" not in inspector.get_table_names():
        return
    existing = {col["name"]: col for col in inspector.get_columns("messages")}
    if "sources" not in existing:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE messages ADD COLUMN sources JSONB"
            ))
    else:
        # 已存在但类型是 JSON，转为 JSONB（统一存储格式）
        col_type = str(existing["sources"]["type"]).upper()
        if "JSON" in col_type and "JSONB" not in col_type:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE messages ALTER COLUMN sources TYPE JSONB USING sources::jsonb"
                ))


def init_db():
    _migrate_users_table()
    _migrate_documents_table()
    Base.metadata.create_all(bind=engine)
    _migrate_documents_status_columns()
    _migrate_messages_sources_column()
