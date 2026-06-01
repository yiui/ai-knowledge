from sqlalchemy.orm import Session

from app.core.minio_client import client as minio_client
from app.core.config import settings
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.services.vector_service import delete_document_vectors


def get_user_knowledge_base(
    db: Session,
    knowledge_base_id: int,
    user_id: int,
) -> KnowledgeBase | None:
    return (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == user_id,
        )
        .first()
    )


def delete_knowledge_base(db: Session, kb: KnowledgeBase) -> None:
    docs = (
        db.query(Document)
        .filter(Document.knowledge_base_id == kb.id)
        .all()
    )

    for doc in docs:
        minio_client.remove_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=doc.path,
        )
        delete_document_vectors(doc.id, kb.id)
        db.delete(doc)

    db.delete(kb)
    db.commit()
