from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
from langchain_huggingface import HuggingFaceEmbeddings

# 使用huggingface的embedding模型
embedding_model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        encode_kwargs={"normalize_embeddings": True}
    )

# def get_embedding():
#     return HuggingFaceEmbeddings(
#         model_name="BAAI/bge-small-zh-v1.5",
#         encode_kwargs={"normalize_embeddings": True}
#     )

def embed_query(text: str):
    return embedding_model.embed_query(text)


def embed_documents(documents):
    texts = [doc.page_content for doc in documents]
    return embedding_model.embed_documents(texts)