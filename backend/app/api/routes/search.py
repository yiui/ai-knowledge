from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.services.vector_store import vector_store

router = APIRouter()


@router.post("/search")
def search(payload: dict, _: User = Depends(get_current_user)):
    query = payload["query"]

    docs = vector_store.similarity_search(query)

    return [
        {"content": doc.page_content}
        for doc in docs
    ]