from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.minio_client import client as minio_client
from app.core.config import settings
from app.models.document import Document
from app.models.user import User
from app.services.document_service import save_file
from app.services.ingest_service import process_document
from app.services.knowledge_base_service import get_user_knowledge_base
from app.services.vector_service import delete_document_vectors

router = APIRouter()


@router.post("/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    knowledge_base_id: int = Query(..., description="目标知识库 ID"),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
):
    kb = get_user_knowledge_base(db, knowledge_base_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    exists = (
        db.query(Document)
        .filter(
            Document.knowledge_base_id == knowledge_base_id,
            Document.filename == file.filename,
        )
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail=f"文件 [{file.filename}] 在该知识库中已存在",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名无效")

    try:
        object_name, size = save_file(file, current_user.id, knowledge_base_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    doc = Document(
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        filename=file.filename,
        path=object_name,
        size=size,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(
        process_document,
        doc.id,
        object_name,
        current_user.id,
        knowledge_base_id,
    )
    return {
        "id": doc.id,
        "filename": doc.filename,
        "path": doc.path,
        "knowledge_base_id": knowledge_base_id,
    }


@router.get("/documents")
def get_documents(
    knowledge_base_id: int = Query(..., description="知识库 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = get_user_knowledge_base(db, knowledge_base_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    docs = (
        db.query(Document)
        .filter(Document.knowledge_base_id == knowledge_base_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "size": format_size(doc.size),
            "created_at": format_time(doc.created_at),
            "knowledge_base_id": doc.knowledge_base_id,
        }
        for doc in docs
    ]


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(
            Document.id == doc_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    kb_id = doc.knowledge_base_id
    db.delete(doc)
    db.commit()
    minio_client.remove_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=doc.path,
    )
    delete_document_vectors(doc_id, kb_id)

    return {"message": "deleted", "id": doc_id}


def format_size(size: int) -> str:
    return f"{round(size / (1024 * 1024), 2)} MB"


def format_time(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
