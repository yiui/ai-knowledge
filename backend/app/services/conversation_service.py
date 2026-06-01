from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message


def count_messages(db: Session, conversation_id: int) -> int:
    return (
        db.query(func.count(Message.id))
        .filter(Message.conversation_id == conversation_id)
        .scalar()
        or 0
    )


def conversation_limits(message_count: int) -> dict:
    max_messages = settings.CHAT_MAX_MESSAGES
    return {
        "message_count": message_count,
        "max_messages": max_messages,
        "should_start_new": message_count >= max_messages,
    }


def get_user_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )


def auto_title_from_question(question: str) -> str:
    text = question.strip().replace("\n", " ")
    if len(text) <= 30:
        return text or "新对话"
    return text[:30] + "…"


def touch_conversation(conversation: Conversation) -> None:
    conversation.updated_at = datetime.now(UTC).replace(tzinfo=None)
