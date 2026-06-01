from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.knowledge_base_service import get_user_knowledge_base
from app.services.vector_service import search_similar

router = APIRouter()


@router.post("/search")
def search(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = payload["query"]
    knowledge_base_id = payload.get("knowledge_base_id")
    if knowledge_base_id is None:
        raise HTTPException(status_code=400, detail="请指定知识库")

    kb = get_user_knowledge_base(db, knowledge_base_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    docs = search_similar(
        query,
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
    )

    return [
        {"content": doc.page_content}
        for doc in docs
    ]
