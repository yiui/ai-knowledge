_embedding_model = None


def _get_embedding_model():
    """延迟创建 embedding model —— 避免模块加载时调用外部 API / 连 Ollama。"""
    global _embedding_model
    if _embedding_model is None:
        from app.core.embeddings import create_embeddings
        _embedding_model = create_embeddings()
    return _embedding_model


def embed_query(text: str):
    return _get_embedding_model().embed_query(text)


def embed_documents(documents):
    texts = [doc.page_content for doc in documents]
    return _get_embedding_model().embed_documents(texts)
