from sqlalchemy import inspect, text

from app.db.session import engine
from app.db.base import Base

# 导入模型（关键，不然不会建表）
from app.models import user  # noqa: F401


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


def init_db():
    _migrate_users_table()
    Base.metadata.create_all(bind=engine)
