import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()


@router.post("/chat")
def chat(payload: dict, current_user: User = Depends(get_current_user)):
    question = payload["question"]
    return chat_service.chat(question, user_id=current_user.id)


@router.post("/chat/stream")
def chat_stream(request: dict, current_user: User = Depends(get_current_user)):
    question = request["question"]

    def event_generator():
        for chunk in chat_service.chat_stream(question, user_id=current_user.id):
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
