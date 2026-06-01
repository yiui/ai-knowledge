from app.services.parser_service import parse_document
from app.services.chunk_service import split_documents
from app.services.embedding_service import embed_documents
from app.services.vector_store import vector_store  
from app.core.minio_client import download_from_minio
from langchain_core.documents import Document
from app.models.document import Document as DocumentModel

def process_document(
    document_id: int,
    file_path: str,
):
    # 0. 下载文件
    local_path = download_from_minio(file_path)

    # 1. 解析
    texts = parse_document(local_path)

    # 2. 分块
    chunks = split_documents(texts)

    # 3. Embedding
    vectors = embed_documents(chunks)
    for chunk in chunks:
        chunk.metadata["document_id"] = document_id
    
    # 4. 保存
    vector_store.add_documents(
        documents=chunks
    )