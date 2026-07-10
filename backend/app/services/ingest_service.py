"""文档向量化编排。

设计要点：
- _do_process_document 是纯执行逻辑，不写状态。
- process_document_with_status 在外层包了：重试、状态写回、/tmp 临时文件清理。
- BackgroundTasks / 僵死恢复线程调 process_document_with_status，路由只写 PENDING 状态后立即返回。
"""
import logging
import os
import time

from app.core.config import settings
from app.core.minio_client import download_from_minio
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus
from app.services.chunk_service import split_documents
from app.services.keyword_service import invalidate_index
from app.services.parser_service import parse_document
from app.services.vector_service import upsert_document_vectors

log = logging.getLogger("ingest")


def _do_process_document(
    document_id: int,
    file_path: str,
    user_id: int,
    knowledge_base_id: int,
    filename: str = "",
) -> int:
    """执行真正的处理流程：下载 → 解析 → 分块 → 向量化 → 写入。

    返回成功写入的 chunk 数。
    """
    local_path = download_from_minio(file_path)
    try:
        texts = parse_document(local_path)
        chunks = split_documents(texts, filename=filename)

        for chunk in chunks:
            chunk.metadata["document_id"] = document_id
            chunk.metadata["user_id"] = str(user_id)
            chunk.metadata["knowledge_base_id"] = str(knowledge_base_id)

        inserted = upsert_document_vectors(
            chunks=chunks,
            document_id=document_id,
            knowledge_base_id=knowledge_base_id,
        )

        # 文档入库后使 BM25 索引失效，下次混合检索时自动重建
        if settings.HYBRID_SEARCH_ENABLED:
            invalidate_index(knowledge_base_id)

        return inserted
    finally:
        # 清理 /tmp 本地副本，避免长期占用磁盘
        try:
            if os.path.exists(local_path):
                os.unlink(local_path)
        except OSError:
            log.warning("failed to cleanup tmp file: %s", local_path)


def _set_status(
    document_id: int,
    *,
    status: str | None = None,
    error_message: str | None = None,
    vector_count: int | None = None,
) -> None:
    """更新 documents 表的状态字段。"""
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if not doc:
            log.warning("document %s not found when setting status", document_id)
            return
        if status is not None:
            doc.status = status
        if error_message is not None:
            doc.error_message = error_message[:1000]
        if vector_count is not None:
            doc.vector_count = vector_count
        db.commit()


def process_document_with_status(
    document_id: int,
    file_path: str,
    user_id: int,
    knowledge_base_id: int,
    filename: str = "",
    *,
    max_retries: int = 3,
) -> bool:
    """带状态写回 + 指数退避的版本。返回 True=ready，False=failed。"""
    # 先标记为 processing
    _set_status(document_id, status=DocumentStatus.PROCESSING.value)

    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            log.info(
                "ingest start doc_id=%s attempt=%s/%s",
                document_id, attempt, max_retries,
            )
            count = _do_process_document(
                document_id, file_path, user_id, knowledge_base_id,
                filename=filename,
            )
            _set_status(
                document_id,
                status=DocumentStatus.READY.value,
                error_message=None,
                vector_count=count,
            )
            log.info(
                "ingest success doc_id=%s chunks=%s", document_id, count,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - 捕获一切交由上层持久化错误
            last_err = exc
            log.exception(
                "ingest failed doc_id=%s attempt=%s/%s err=%s",
                document_id, attempt, max_retries, exc,
            )
            if attempt < max_retries:
                # 指数退避：1s / 2s / 4s ...
                time.sleep(2 ** (attempt - 1))

    _set_status(
        document_id,
        status=DocumentStatus.FAILED.value,
        error_message=str(last_err) if last_err else "unknown error",
    )
    return False


# —— 保留兼容：旧 process_document 入口（让 BackgroundTasks 之类的旧调用仍可工作） ——
def process_document(
    document_id: int,
    file_path: str,
    user_id: int,
    knowledge_base_id: int,
    filename: str = "",
) -> None:
    """兼容旧 BackgroundTasks 调用的入口。

    不会再有"上传成功但无状态"的场景：失败至少会写 failed 状态。
    """
    process_document_with_status(
        document_id, file_path, user_id, knowledge_base_id,
        filename=filename,
    )
