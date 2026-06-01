from app.db.session import engine
from app.db.base import Base

# 导入模型（关键，不然不会建表）
from app.models import user  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)