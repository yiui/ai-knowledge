from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_service import chat_with_ai

router = APIRouter()

class ChatRequest(BaseModel):
    question: str


@router.post("/chat")
def chat(req: ChatRequest):
    answer = chat_with_ai(req.question)
    return {
        "question": req.question,
        "answer": answer
    }