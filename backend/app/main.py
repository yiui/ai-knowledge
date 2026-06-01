from app.db.init_db import init_db
from fastapi import FastAPI
from app.api.routes.llm import router as llm_router
from app.api.routes.documents import router as doc_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware 
from app.api.routes.chat import router as chat_router
from app.api.routes.search import router as search_router
from app.api.routes.auth import router as auth_router
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
app.include_router(doc_router)
app.include_router(chat_router)
app.include_router(search_router)
@app.on_event("startup")
def on_startup():
    init_db()


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
    else:
        llm_config["model"] = settings.OLLAMA_MODEL
        llm_config["base_url"] = settings.OLLAMA_BASE_URL

    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "llm": llm_config,
    }