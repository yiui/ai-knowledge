from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.session import engine

# 导入模型（关键，不然不会建表）
from app.models import document, user  # noqa: F401


def _migrate_users_table() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    required = {"username", "password_hash"}
    if required.issubset(columns):
        return

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))


def _migrate_documents_table() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("documents")}
    if "user_id" in columns:
        return

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))
        if "langchain_pg_embedding" in inspector.get_table_names():
            conn.execute(text("DELETE FROM langchain_pg_embedding"))


def init_db():
    _migrate_users_table()
    _migrate_documents_table()
    Base.metadata.create_all(bind=engine)
