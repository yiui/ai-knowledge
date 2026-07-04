from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)


def _sanitize_text(text: str) -> str:
    """移除 NUL 等 PostgreSQL 不能存储的字符。"""
    if not text:
        return text
    # \x00 (NUL) 会导致 psycopg2 报错 "A string literal cannot contain NUL"
    return text.replace("\x00", "")


def split_documents(texts: list[str]):
    # 先把原始文本里的 NUL 清掉，避免传播到每个 chunk
    clean_texts = [_sanitize_text(t) for t in texts]
    chunks = splitter.create_documents(clean_texts)

    # 再把每个 chunk 的 page_content 也清一遍，双重保险
    for chunk in chunks:
        chunk.page_content = _sanitize_text(chunk.page_content)

    return chunks