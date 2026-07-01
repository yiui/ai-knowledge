from app.core.embeddings import create_embeddings

embedding_model = create_embeddings()


def embed_query(text: str):
    return embedding_model.embed_query(text)


def embed_documents(documents):
    texts = [doc.page_content for doc in documents]
    return embedding_model.embed_documents(texts)
