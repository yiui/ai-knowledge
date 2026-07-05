from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["gemini", "ollama", "deepseek", "bailian"]
EmbeddingProvider = Literal["openai_compat", "ollama"]
RerankProvider = Literal["openai_compat", "dashscope", "ollama"]


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool

    LLM_PROVIDER: LLMProvider

    # 统一 LLM 配置（所有 provider 通用）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""

    # 生成参数
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_TOP_P: float = 0.9

    # Embedding: openai_compat（阿里云百炼等 OpenAI 兼容接口）| ollama
    EMBEDDING_PROVIDER: EmbeddingProvider = "openai_compat"
    EMBEDDING_MODEL: str = "text-embedding-v4"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    # text-embedding-v4 可选维度；0 表示使用模型默认
    EMBEDDING_DIMENSIONS: int = 0
    # openai_compat 单次请求最大条数（百炼 text-embedding-v4 上限 20）
    EMBEDDING_BATCH_SIZE: int = 20

    # 百炼新版 sk-ws 密钥需配置业务空间 ID（控制台 → 业务空间详情）
    DASHSCOPE_WORKSPACE_ID: str = ""
    DASHSCOPE_REGION: str = "cn-beijing"

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str
    MINIO_SECURE: bool

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    RERANK_ENABLED: bool = True
    # openai_compat: 百炼 qwen3-rerank | dashscope: gte-rerank-v2 等 | ollama: /api/rerank
    RERANK_PROVIDER: RerankProvider = "openai_compat"
    RERANK_MODEL: str = "qwen3-rerank"
    RERANK_API_KEY: str = ""
    # 留空则按 DASHSCOPE_WORKSPACE_ID 自动拼接；sk-ws 密钥必填 workspace
    RERANK_BASE_URL: str = ""
    RERANK_INSTRUCT: str = ""
    RERANK_TIMEOUT_SECONDS: float = 60.0
    VECTOR_RECALL_K: int = 20
    RERANK_TOP_K: int = 4

    # 混合检索：向量 + BM25 关键词
    HYBRID_SEARCH_ENABLED: bool = True
    KEYWORD_RECALL_K: int = 20

    CHAT_MAX_MESSAGES: int = 50

    UPLOAD_ALLOWED_EXTENSIONS: str = "pdf,txt,md,xlsx,xls"
    UPLOAD_MAX_SIZE_MB: int = 20

    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_RECYCLE: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @staticmethod
    def _normalize_optional_http_url(value: str, field_name: str) -> str:
        normalized = value.strip()
        for prefix in (f"{field_name}=", "RERANK_BASE_URL=", "EMBEDDING_BASE_URL="):
            if normalized.startswith(prefix):
                normalized = normalized.removeprefix(prefix).strip()
        if normalized and not normalized.startswith(("http://", "https://")):
            raise ValueError(
                f"{field_name} must start with http:// or https://, got: {normalized!r}"
            )
        return normalized

    @field_validator("RERANK_BASE_URL", mode="before")
    @classmethod
    def normalize_rerank_base_url(cls, value: object) -> object:
        if isinstance(value, str):
            return cls._normalize_optional_http_url(value, "RERANK_BASE_URL")
        return value

    @field_validator("EMBEDDING_BASE_URL", mode="before")
    @classmethod
    def normalize_embedding_base_url(cls, value: object) -> object:
        if isinstance(value, str):
            return cls._normalize_optional_http_url(value, "EMBEDDING_BASE_URL")
        return value

    @model_validator(mode="after")
    def validate_llm_config(self) -> "Settings":
        if self.LLM_PROVIDER == "gemini":
            if not self.llm_api_key:
                raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=gemini")
            if not self.llm_model:
                raise ValueError("LLM_MODEL is required when LLM_PROVIDER=gemini")
        elif self.LLM_PROVIDER == "ollama":
            if not self.llm_base_url:
                raise ValueError("LLM_BASE_URL is required when LLM_PROVIDER=ollama")
            if not self.llm_model:
                raise ValueError("LLM_MODEL is required when LLM_PROVIDER=ollama")
        elif self.LLM_PROVIDER == "deepseek":
            if not self.llm_api_key:
                raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=deepseek")
            if not self.llm_model:
                raise ValueError("LLM_MODEL is required when LLM_PROVIDER=deepseek")
        elif self.LLM_PROVIDER == "bailian":
            if not self.llm_api_key:
                raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=bailian")
            if not self.llm_model:
                raise ValueError("LLM_MODEL is required when LLM_PROVIDER=bailian")

        if self.EMBEDDING_PROVIDER == "openai_compat":
            if not self.EMBEDDING_API_KEY.strip():
                raise ValueError(
                    "EMBEDDING_API_KEY is required when EMBEDDING_PROVIDER=openai_compat"
                )
            if not self.EMBEDDING_BASE_URL.strip():
                raise ValueError(
                    "EMBEDDING_BASE_URL is required when EMBEDDING_PROVIDER=openai_compat"
                )
            if not self.EMBEDDING_MODEL.strip():
                raise ValueError(
                    "EMBEDDING_MODEL is required when EMBEDDING_PROVIDER=openai_compat"
                )
        elif self.EMBEDDING_PROVIDER == "ollama":
            if not self.EMBEDDING_MODEL.strip():
                raise ValueError("EMBEDDING_MODEL is required when EMBEDDING_PROVIDER=ollama")
            if not self.EMBEDDING_BASE_URL.strip():
                raise ValueError(
                    "EMBEDDING_BASE_URL is required "
                    "when EMBEDDING_PROVIDER=ollama"
                )

        if self.RERANK_ENABLED:
            if self.RERANK_PROVIDER in {"openai_compat", "dashscope"}:
                if not self.rerank_api_key.strip():
                    raise ValueError(
                        f"RERANK_API_KEY is required when RERANK_PROVIDER={self.RERANK_PROVIDER}"
                    )
                if not self.rerank_api_url.strip():
                    raise ValueError(
                        f"RERANK_BASE_URL is required when RERANK_PROVIDER={self.RERANK_PROVIDER}"
                    )
            elif self.RERANK_PROVIDER == "ollama":
                if not self.RERANK_MODEL.strip():
                    raise ValueError("RERANK_MODEL is required when RERANK_PROVIDER=ollama")
                if not self.RERANK_BASE_URL.strip():
                    raise ValueError(
                        "RERANK_BASE_URL is required "
                        "when RERANK_PROVIDER=ollama"
                    )
            if not self.RERANK_MODEL.strip():
                raise ValueError("RERANK_MODEL is required when RERANK_ENABLED=true")
        return self

    @property
    def rerank_api_key(self) -> str:
        return self.RERANK_API_KEY.strip()

    @property
    def dashscope_workspace_host(self) -> str | None:
        workspace_id = self.DASHSCOPE_WORKSPACE_ID.strip()
        if not workspace_id:
            return None
        region = self.DASHSCOPE_REGION.strip() or "cn-beijing"
        return f"https://{workspace_id}.{region}.maas.aliyuncs.com"

    @property
    def rerank_api_url(self) -> str:
        if self.RERANK_BASE_URL.strip():
            return self.RERANK_BASE_URL.strip()
        if host := self.dashscope_workspace_host:
            if self.RERANK_PROVIDER == "openai_compat":
                return f"{host}/compatible-api/v1/reranks"
            return f"{host}/api/v1/services/rerank/text-rerank/text-rerank"
        if self.RERANK_PROVIDER == "openai_compat":
            return "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
        return "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

    @property
    def allowed_upload_extensions(self) -> set[str]:
        return {
            ext.strip().lower().lstrip(".")
            for ext in self.UPLOAD_ALLOWED_EXTENSIONS.split(",")
            if ext.strip()
        }

    @property
    def UPLOAD_MAX_SIZE_BYTES(self) -> int:
        return int(self.UPLOAD_MAX_SIZE_MB) * 1024 * 1024

    # ---- LLM computed properties ----

    @property
    def llm_api_key(self) -> str:
        return self.LLM_API_KEY.strip()

    @property
    def llm_base_url(self) -> str:
        if self.LLM_BASE_URL.strip():
            return self.LLM_BASE_URL.strip()
        # provider 默认值
        match self.LLM_PROVIDER:
            case "deepseek":
                return "https://api.deepseek.com"
            case "bailian":
                host = self.dashscope_workspace_host
                if host:
                    return f"{host}/compatible-mode/v1"
                return "https://dashscope.aliyuncs.com/compatible-mode/v1"
            case _:
                return ""

    @property
    def llm_model(self) -> str:
        if self.LLM_MODEL.strip():
            return self.LLM_MODEL.strip()
        # provider 默认模型
        match self.LLM_PROVIDER:
            case "deepseek":
                return "deepseek-chat"
            case "bailian":
                return "qwen-plus"
            case _:
                return ""

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()

