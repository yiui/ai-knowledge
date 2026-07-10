from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
)


def _sanitize_text(text: str) -> str:
    """移除 NUL 等 PostgreSQL 不能存储的字符。"""
    if not text:
        return text
    # \x00 (NUL) 会导致 psycopg2 报错 "A string literal cannot contain NUL"
    return text.replace("\x00", "")


def split_documents(texts: list[str], filename: str = ""):
    """将文本切分为 chunk，并附加序号元数据和文档头。

    每个 chunk 的 page_content 会加上前缀：
        [文档: report.pdf | 片段 3/12]
    以便 LLM 理解 chunk 之间的结构关系，解决跨 chunk 知识点断裂问题。
    """
    clean_texts = [_sanitize_text(t) for t in texts]
    raw_chunks = splitter.create_documents(clean_texts)

    total = len(raw_chunks)
    for i, chunk in enumerate(raw_chunks):
        chunk.page_content = _sanitize_text(chunk.page_content)
        chunk.metadata["chunk_index"] = i
        chunk.metadata["chunk_total"] = total

    # 拼接元数据头：让 LLM 感知 chunk 在文档中的位置
    if filename and total > 1:
        for i, chunk in enumerate(raw_chunks):
            header = f"[文档: {filename} | 片段 {i + 1}/{total}]\n"
            chunk.page_content = header + chunk.page_content

    return raw_chunks
