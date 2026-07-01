from app.core.minio_client import download_from_minio
from app.services.chunk_service import split_documents
from app.services.parser_service import parse_document
from app.services.vector_store import vector_store


def process_document(
    document_id: int,
    file_path: str,
    user_id: int,
    knowledge_base_id: int,
):
    local_path = download_from_minio(file_path)

    texts = parse_document(local_path)
    chunks = split_documents(texts)

    for chunk in chunks:
        chunk.metadata["document_id"] = document_id
        chunk.metadata["user_id"] = str(user_id)
        chunk.metadata["knowledge_base_id"] = str(knowledge_base_id)

    vector_store.add_documents(documents=chunks)
