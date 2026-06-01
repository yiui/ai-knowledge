from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.minio_client import client as minio_client
from app.core.config import settings
from app.models.document import Document
from app.models.user import User
from app.services.document_service import save_file
from app.services.ingest_service import process_document
from app.services.vector_service import delete_document_vectors

router = APIRouter()


@router.post("/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
):
    exists = (
        db.query(Document)
        .filter(
            Document.user_id == current_user.id,
            Document.filename == file.filename,
        )
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail=f"文件 [{file.filename}] 已存在",
        )

    object_name, size = save_file(file, current_user.id)

    doc = Document(
        user_id=current_user.id,
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
    )
    return {
        "id": doc.id,
        "filename": doc.filename,
        "path": doc.path,
    }


@router.get("/documents")
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "size": format_size(doc.size),
            "created_at": format_time(doc.created_at),
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

    db.delete(doc)
    db.commit()
    minio_client.remove_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=doc.path,
    )
    delete_document_vectors(doc_id, current_user.id)

    return {"message": "deleted", "id": doc_id}


def format_size(size: int) -> str:
    return f"{round(size / (1024 * 1024), 2)} MB"


def format_time(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
