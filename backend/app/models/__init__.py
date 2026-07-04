"""Models package —— 统一导入，确保 Base.metadata 收集所有表定义。"""

from app.models.conversation import Conversation  # noqa: F401
from app.models.document import Document, DocumentStatus  # noqa: F401
from app.models.knowledge_base import KnowledgeBase  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.user import User  # noqa: F401
