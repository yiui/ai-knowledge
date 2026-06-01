from langchain_postgres import PGVector

from app.core.config import settings

from app.services.embedding_service import (
    embedding_model
)

vector_store = PGVector(
    embeddings=embedding_model,
    collection_name="knowledge",
    connection=settings.DATABASE_URL,
)