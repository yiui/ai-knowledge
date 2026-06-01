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
    _: User = Depends(get_current_user),
):
    # 检查同名文件
    exists = (
        db.query(Document)
        .filter(Document.filename == file.filename)
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail=f"文件 [{file.filename}] 已存在"
        )

# 1. 上传 MinIO 存储
    object_name, size = save_file(file)

    # 2. 记录到数据库
    doc = Document(
        filename=file.filename,
        path=object_name,
        size=size
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

        # 3. 知识库处理 入库    
    # process_document(doc.id, object_name)
  # ⭐ 关键：丢到后台执行
    background_tasks.add_task(process_document, doc.id, object_name)
    return {
        "id": doc.id,
        "filename": doc.filename,
        "path": doc.path
    }


# 获取所有文档
@router.get("/documents")
def get_documents(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "size": format_size(doc.size),
            "created_at": format_time(doc.created_at)
        }
        for doc in docs
    ]



# 删除文档
@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()

    if not doc:
        return {"message": "not found"}

    db.delete(doc)
    db.commit()
    # 删除 MinIO 存储
    minio_client.remove_object(bucket_name=settings.MINIO_BUCKET, object_name=doc.path)
    # 删除向量
    delete_document_vectors(doc_id)

    return {"message": "deleted", "id": doc_id}

def format_size(size: int) -> str:
    return f"{round(size / (1024 * 1024), 2)} MB"

def format_time(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")