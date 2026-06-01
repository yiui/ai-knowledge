import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()


@router.post("/chat")
def chat(payload: dict, _: User = Depends(get_current_user)):
    question = payload["question"]
    return chat_service.chat(question)


@router.post("/chat/stream")
def chat_stream(request: dict, _: User = Depends(get_current_user)):
    question = request["question"]

    def event_generator():
        for chunk in chat_service.chat_stream(question):
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
