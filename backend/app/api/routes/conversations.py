import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import (
    ChatLimitsResponse,
    ChatStreamRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    MessageResponse,
)
from app.services.chat_service import ChatService
from app.services.conversation_service import (
    auto_title_from_question,
    conversation_limits,
    count_messages,
    get_user_conversation,
    touch_conversation,
)
from app.db.session import SessionLocal
from app.services.knowledge_base_service import get_user_knowledge_base

router = APIRouter(prefix="/conversations", tags=["conversations"])
chat_service = ChatService()


def _resolve_kb_id(
    db: Session,
    user_id: int,
    knowledge_base_id: int | None,
) -> int | None:
    if knowledge_base_id is None:
        return None
    kb = get_user_knowledge_base(db, knowledge_base_id, user_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return knowledge_base_id


def _to_summary(db: Session, conv: Conversation) -> ConversationSummary:
    msg_count = count_messages(db, conv.id)
    limits = conversation_limits(msg_count)
    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        knowledge_base_id=conv.knowledge_base_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        **limits,
    )


@router.get("/limits", response_model=ChatLimitsResponse)
def get_chat_limits():
    return ChatLimitsResponse(
        max_messages_per_conversation=settings.CHAT_MAX_MESSAGES,
    )


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [_to_summary(db, conv) for conv in convs]


@router.post("", response_model=ConversationSummary, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb_id = _resolve_kb_id(db, current_user.id, payload.knowledge_base_id)
    conv = Conversation(
        user_id=current_user.id,
        title=payload.title or "新对话",
        knowledge_base_id=kb_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _to_summary(db, conv)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = get_user_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    msg_count = count_messages(db, conv.id)
    limits = conversation_limits(msg_count)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        knowledge_base_id=conv.knowledge_base_id,
        messages=[MessageResponse.model_validate(m) for m in conv.messages],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        **limits,
    )


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = get_user_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    if payload.title is not None:
        conv.title = payload.title
    if "knowledge_base_id" in payload.model_fields_set:
        if payload.knowledge_base_id is None:
            conv.knowledge_base_id = None
        else:
            conv.knowledge_base_id = _resolve_kb_id(
                db,
                current_user.id,
                payload.knowledge_base_id,
            )

    touch_conversation(conv)
    db.commit()
    db.refresh(conv)
    return _to_summary(db, conv)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = get_user_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.delete(conv)
    db.commit()
    return {"message": "deleted", "id": conversation_id}


@router.post("/{conversation_id}/chat/stream")
def chat_stream_in_conversation(
    conversation_id: int,
    payload: ChatStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = get_user_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    msg_count = count_messages(db, conv.id)
    if msg_count >= settings.CHAT_MAX_MESSAGES:
        raise HTTPException(
            status_code=400,
            detail=f"当前会话消息已达 {settings.CHAT_MAX_MESSAGES} 条上限，请开启新会话",
        )

    question = payload.question.strip()
    user_message = Message(
        conversation_id=conv.id,
        role="user",
        content=question,
    )
    db.add(user_message)

    if conv.title == "新对话" or not conv.title.strip():
        conv.title = auto_title_from_question(question)

    touch_conversation(conv)
    db.commit()

    kb_id = conv.knowledge_base_id
    conv_id = conv.id
    user_id = current_user.id

    def event_generator():
        chunks: list[str] = []
        sources_data: list[dict] | None = None
        try:
            for item in chat_service.chat_stream(question, user_id, kb_id):
                if isinstance(item, dict):
                    if "sources" in item:
                        sources_data = item["sources"]
                    yield f"data: {json.dumps(item)}\n\n"
                else:
                    chunks.append(item)
                    yield f"data: {json.dumps({'text': item})}\n\n"
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger("chat").exception("stream failed")
            err_msg = f"请求失败: {exc}"
            yield f"data: {json.dumps({'text': err_msg})}\n\n"
            chunks.append(err_msg)
        finally:
            answer = "".join(chunks)
            save_db = SessionLocal()
            try:
                assistant_message = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=answer or "（无回复）",
                    sources=sources_data,
                )
                save_db.add(assistant_message)
                conv_row = save_db.query(Conversation).filter(
                    Conversation.id == conv_id
                ).first()
                if conv_row:
                    touch_conversation(conv_row)
                save_db.commit()

                new_count = count_messages(save_db, conv_id)
                limits = conversation_limits(new_count)
                yield f"data: {json.dumps({'done': True, **limits})}\n\n"
            finally:
                save_db.close()
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
