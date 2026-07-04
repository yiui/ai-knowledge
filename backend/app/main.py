from app.db.init_db import init_db
from fastapi import FastAPI
from app.api.routes.llm import router as llm_router
from app.api.routes.documents import router as doc_router
from app.core.config import settings
from app.core.upload import upload_limits_payload
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.chat import router as chat_router
from app.api.routes.search import router as search_router
from app.api.routes.auth import router as auth_router
from app.api.routes.knowledge_bases import router as kb_router
from app.api.routes.conversations import router as conversations_router
from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.models.document import Document
from datetime import datetime, timedelta,timezone
import threading
import time
import logging

log = logging.getLogger("startup")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)
# 跨域处理
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm_router, prefix="/api")
app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(doc_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(search_router)

# 定时恢复卡住的任务
_stale_recovery_stop = False
_stale_recovery_thread: threading.Thread | None = None


def _stale_recovery_loop():
    """后台线程：每 5 分钟回收卡住的任务。

    分两步，避免与仍在运行的 BackgroundTask 并发处理同一文档：
    1. 僵死 processing（updated_at > 10 min 未更新）→ 只重置为 pending，不处理
    2. 冷却期已过的 pending（updated_at > 5 min，即非刚重置、非活跃 BackgroundTask）
       → 批量同步处理

    刚重置的文档 updated_at 被刷新，不会在本轮被 step 2 捞到，
    下一轮（5 min 后）冷却期已过才会被处理。
    """
    from app.services.ingest_service import process_document_with_status

    global _stale_recovery_stop
    log.info("stale recovery loop started")
    while not _stale_recovery_stop:
        try:
            # 1. 回收僵死 processing → pending（只重置，不处理）
            with engine.begin() as conn:
                result = conn.execute(
                    text("""
                        UPDATE documents
                        SET status = 'pending', error_message = NULL, updated_at = NOW()
                        WHERE status = 'processing'
                          AND updated_at < NOW() - INTERVAL '10 minutes'
                    """)
                )
                if result.rowcount > 0:
                    log.info(
                        "stale recovery: reset %s stale processing → pending",
                        result.rowcount,
                    )

            # 2. 批量处理冷却期已过的 pending 文档
            cooldown = datetime.now(timezone.utc) - timedelta(minutes=5)
            with SessionLocal() as db:
                orphans = (
                    db.query(Document)
                    .filter(
                        Document.status == "pending",
                        Document.updated_at < cooldown,
                    )
                    .order_by(Document.created_at)
                    .all()
                )

            for doc in orphans:
                log.info("stale recovery: processing pending doc_id=%s", doc.id)
                try:
                    process_document_with_status(
                        document_id=doc.id,
                        file_path=doc.path,
                        user_id=doc.user_id,
                        knowledge_base_id=doc.knowledge_base_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    log.exception(
                        "stale recovery: pending process failed doc_id=%s: %s",
                        doc.id, exc,
                    )

        except Exception as exc:  # noqa: BLE001
            log.exception("stale recovery loop error: %s", exc)

        # 等待 5 分钟（用小块 sleep 以便快速退出）
        for _ in range(300):
            if _stale_recovery_stop:
                break
            time.sleep(1)


@app.on_event("startup")
def on_startup():
    init_db()
    global _stale_recovery_thread
    _stale_recovery_thread = threading.Thread(
        target=_stale_recovery_loop,
        daemon=True,
        name="stale-recovery",
    )
    _stale_recovery_thread.start()


@app.on_event("shutdown")
def on_shutdown():
    global _stale_recovery_stop
    _stale_recovery_stop = True
    log.info("stale recovery loop stopped")


@app.get("/")
async def root():
    return {
        "message": settings.APP_NAME
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }

@app.get("/config")
async def config():
    llm_config = {
        "provider": settings.LLM_PROVIDER,
    }
    if settings.LLM_PROVIDER == "gemini":
        llm_config["model"] = settings.GEMINI_MODEL
    elif settings.LLM_PROVIDER == "deepseek":
        llm_config["model"] = settings.DEEPSEEK_MODEL
        llm_config["base_url"] = settings.DEEPSEEK_BASE_URL
    else:
        llm_config["model"] = settings.OLLAMA_MODEL
        llm_config["base_url"] = settings.OLLAMA_BASE_URL

    embedding_config = {
        "provider": settings.EMBEDDING_PROVIDER,
        "model": settings.EMBEDDING_MODEL,
    }
    if settings.EMBEDDING_PROVIDER == "openai_compat":
        embedding_config["base_url"] = settings.EMBEDDING_BASE_URL
        if settings.EMBEDDING_DIMENSIONS > 0:
            embedding_config["dimensions"] = settings.EMBEDDING_DIMENSIONS
    else:
        embedding_config["base_url"] = settings.embedding_base_url

    rerank_config = {
        "enabled": settings.RERANK_ENABLED,
        "provider": settings.RERANK_PROVIDER,
        "model": settings.RERANK_MODEL,
    }
    if settings.RERANK_PROVIDER in {"openai_compat", "dashscope"}:
        rerank_config["base_url"] = settings.rerank_api_url
    elif settings.RERANK_PROVIDER == "ollama":
        rerank_config["base_url"] = settings.rerank_base_url_ollama

    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "llm": llm_config,
        "embedding": embedding_config,
        "rerank": rerank_config,
        "chat": {
            "max_messages_per_conversation": settings.CHAT_MAX_MESSAGES,
        },
        "upload": upload_limits_payload(),
    }