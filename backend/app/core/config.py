from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["gemini", "ollama"]


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool

    LLM_PROVIDER: LLMProvider
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str

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
    RERANK_MODEL: str = "BAAI/bge-reranker-base"
    VECTOR_RECALL_K: int = 20
    RERANK_TOP_K: int = 4

    CHAT_MAX_MESSAGES: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_llm_config(self) -> "Settings":
        if self.LLM_PROVIDER == "gemini":
            if not self.GEMINI_API_KEY.strip():
                raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
            if not self.GEMINI_MODEL.strip():
                raise ValueError("GEMINI_MODEL is required when LLM_PROVIDER=gemini")
        elif self.LLM_PROVIDER == "ollama":
            if not self.OLLAMA_BASE_URL.strip():
                raise ValueError("OLLAMA_BASE_URL is required when LLM_PROVIDER=ollama")
            if not self.OLLAMA_MODEL.strip():
                raise ValueError("OLLAMA_MODEL is required when LLM_PROVIDER=ollama")
        return self

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()

