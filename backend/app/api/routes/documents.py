from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.minio_client import client as minio_client
from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.services.document_service import save_file
from app.services.ingest_service import process_document
from app.services.knowledge_base_service import get_user_knowledge_base
from app.services.vector_service import delete_document_vectors

router = APIRouter()


@router.post("/documents/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge_base_id: int = Query(..., description="目标知识库 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档。

    行为：
    - 同步部分：MinIO 上传 + Document 行插入（status=pending）。
    - 异步部分：BackgroundTasks 调用 process_document，处理完成后状态变为 ready/failed。
    - 返回新增 status / vector_count 字段，前端可轮询。
    """
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
        status=DocumentStatus.PENDING.value,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 用 BackgroundTasks 异步处理，进程重启时会丢失当前正在处理的任务，
    # 但 pending 状态的行还在 DB 里，定时任务会捡回来。
    background_tasks.add_task(
        process_document,
        doc.id,
        doc.path,
        current_user.id,
        knowledge_base_id,
    )

    return {
        "id": doc.id,
        "filename": doc.filename,
        "path": doc.path,
        "knowledge_base_id": knowledge_base_id,
        "size": format_size(doc.size),
        "status": doc.status,
        "vector_count": doc.vector_count,
        "error_message": doc.error_message,
        "created_at": format_time(doc.created_at),
    }


@router.get("/documents")
def get_documents(
    knowledge_base_id: int = Query(..., description="知识库 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    search: str | None = Query(None, description="按文件名搜索"),
    status: str | None = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = get_user_knowledge_base(db, knowledge_base_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    base_q = (
        db.query(Document)
        .filter(Document.knowledge_base_id == knowledge_base_id)
    )

    if search:
        base_q = base_q.filter(Document.filename.ilike(f"%{search}%"))
    if status:
        base_q = base_q.filter(Document.status == status)

    total = base_q.count()

    docs = (
        base_q
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        {
            "id": doc.id,
            "filename": doc.filename,
            "size": format_size(doc.size),
            "created_at": format_time(doc.created_at),
            "knowledge_base_id": doc.knowledge_base_id,
            "status": doc.status,
            "error_message": doc.error_message,
            "vector_count": doc.vector_count,
        }
        for doc in docs
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/documents/{doc_id}/reindex")
def reindex_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把文档从 failed / processing 重新置为 pending，通过 BackgroundTasks 重新处理。

    适用于：Embedding 临时故障修复后、用户主动重试。
    """
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

    if doc.status not in (DocumentStatus.FAILED.value, DocumentStatus.PROCESSING.value):
        raise HTTPException(
            status_code=400,
            detail=f"当前状态 [{doc.status}] 不支持重试，仅 failed/processing 可重试",
        )

    doc.status = DocumentStatus.PENDING.value
    doc.error_message = None
    doc.vector_count = 0
    db.commit()

    background_tasks.add_task(
        process_document,
        doc.id,
        doc.path,
        current_user.id,
        doc.knowledge_base_id,
    )

    return {
        "id": doc.id,
        "status": doc.status,
        "message": "已提交重试，正在重新向量化",
    }


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


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/documents/batch-delete")
def batch_delete_documents(
    body: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除文档（仅删除属于当前用户的文档）。"""
    if not body.ids:
        raise HTTPException(status_code=400, detail="请提供要删除的文档 ID 列表")

    docs = (
        db.query(Document)
        .filter(
            Document.id.in_(body.ids),
            Document.user_id == current_user.id,
        )
        .all()
    )

    deleted = 0
    for doc in docs:
        kb_id = doc.knowledge_base_id
        db.delete(doc)
        minio_client.remove_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=doc.path,
        )
        delete_document_vectors(doc.id, kb_id)
        deleted += 1

    db.commit()

    return {"message": f"已删除 {deleted} 个文档", "deleted": deleted}


def format_size(size: int) -> str:
    return f"{round(size / (1024 * 1024), 2)} MB"


def format_time(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
