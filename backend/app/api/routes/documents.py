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
from app.services.vector_service import delete_document_vectors, get_document_chunks

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
        file.filename,
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


@router.get("/documents/status")
def get_document_statuses(
    knowledge_base_id: int = Query(..., description="知识库 ID"),
    ids: str = Query(..., description="逗号分隔的文档 ID 列表，如 1,3,7"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """轻量端点：仅返回指定文档的 status / vector_count / error_message。
    前端轮询用，避免每次都拉全量分页列表。
    """
    kb = get_user_knowledge_base(db, knowledge_base_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    if not id_list:
        return []

    docs = (
        db.query(Document)
        .filter(
            Document.id.in_(id_list),
            Document.knowledge_base_id == knowledge_base_id,
            Document.user_id == current_user.id,
        )
        .all()
    )

    return [
        {
            "id": doc.id,
            "status": doc.status,
            "vector_count": doc.vector_count,
            "error_message": doc.error_message,
        }
        for doc in docs
    ]


@router.post("/documents/{doc_id}/reindex")
def reindex_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新处理文档：重新下载 → 解析 → 分块 → 向量化。

    任意状态均可调用，用于分块参数变更后批量重建向量。
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
        doc.filename,
    )

    return {
        "id": doc.id,
        "status": doc.status,
        "message": "已提交重处理，正在重新向量化",
    }


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/documents/batch-reindex")
def batch_reindex_documents(
    body: BatchDeleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量重新处理文档：重置为 pending 并触发后台向量化任务。"""
    if not body.ids:
        raise HTTPException(status_code=400, detail="请提供要重处理的文档 ID 列表")

    docs = (
        db.query(Document)
        .filter(
            Document.id.in_(body.ids),
            Document.user_id == current_user.id,
        )
        .all()
    )

    for doc in docs:
        doc.status = DocumentStatus.PENDING.value
        doc.error_message = None
        doc.vector_count = 0

    db.commit()

    for doc in docs:
        background_tasks.add_task(
            process_document,
            doc.id,
            doc.path,
            current_user.id,
            doc.knowledge_base_id,
            doc.filename,
        )

    return {"message": f"已提交 {len(docs)} 个文档的重处理任务", "count": len(docs)}


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


@router.get("/documents/{doc_id}/chunks")
def document_chunks(
    doc_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回文档的分块，按 chunk_index 排序，支持分页。用于预览。"""
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

    chunks = get_document_chunks(
        doc.id, doc.knowledge_base_id, current_user.id,
        page=page, page_size=page_size,
    )
    return {
        "document": {
            "id": doc.id,
            "filename": doc.filename,
            "size": format_size(doc.size),
            "status": doc.status,
        },
        "chunks": chunks,
    }


def format_size(size: int) -> str:
    return f"{round(size / (1024 * 1024), 2)} MB"


def format_time(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
