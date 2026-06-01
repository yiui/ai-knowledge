import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.chat_service import ChatService
from app.services.knowledge_base_service import get_user_knowledge_base

router = APIRouter()
chat_service = ChatService()


def _resolve_knowledge_base_id(
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


@router.post("/chat")
def chat(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = payload["question"]
    kb_id = _resolve_knowledge_base_id(
        db,
        current_user.id,
        payload.get("knowledge_base_id"),
    )
    return chat_service.chat(question, current_user.id, kb_id)


@router.post("/chat/stream")
def chat_stream(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = request["question"]
    kb_id = _resolve_knowledge_base_id(
        db,
        current_user.id,
        request.get("knowledge_base_id"),
    )

    def event_generator():
        for chunk in chat_service.chat_stream(question, current_user.id, kb_id):
            yield f"data: {json.dumps({'text': chunk})}\n\n"

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
