from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.services.vector_service import search_similar

router = APIRouter()


@router.post("/search")
def search(payload: dict, current_user: User = Depends(get_current_user)):
    query = payload["query"]
    docs = search_similar(query, user_id=current_user.id)

    return [
        {"content": doc.page_content}
        for doc in docs
    ]
