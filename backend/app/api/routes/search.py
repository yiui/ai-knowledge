from fastapi import APIRouter
from app.services.vector_store import vector_store

router = APIRouter()

@router.post("/search")
def search(payload: dict):
    query = payload["query"]

    docs = vector_store.similarity_search(query)

    return [
        {"content": doc.page_content}
        for doc in docs
    ]