from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)


def split_documents(texts: list[str]) -> list[str]:

    chunks = splitter.create_documents(texts)

    return chunks