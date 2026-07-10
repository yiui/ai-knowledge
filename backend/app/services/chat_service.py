from collections.abc import Iterator
from typing import Union

from app.core.config import settings
from app.core.llm import ask_llm, stream_llm
from app.services.vector_service import search_hybrid, search_similar, get_adjacent_chunks


def _extract_source_meta(docs: list) -> list[dict]:
    """从 LangChain Document 列表中提取来源元数据。"""
    seen = set()
    sources: list[dict] = []
    for d in docs:
        filename = d.metadata.get("filename", "")
        chunk_index = d.metadata.get("chunk_index")
        chunk_total = d.metadata.get("chunk_total")
        key = (filename, chunk_index)
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "filename": filename,
            "chunk_index": chunk_index if chunk_index is not None else 0,
            "chunk_total": chunk_total if chunk_total is not None else 0,
        })
    # 按文件名 + 片段号排序
    sources.sort(key=lambda s: (s["filename"], s["chunk_index"]))
    return sources


class ChatService:

    def _build_direct_prompt(self, question: str, *, stream: bool = False) -> str:
        if stream:
            return f"""
你是智能助手。请用清晰、友好的方式回答用户的问题。

问题：
{question}
"""
        return f"""
你是智能助手。请用清晰、友好的方式回答用户的问题。

问题：
{question}
"""

    def _build_rag_prompt(
        self,
        question: str,
        user_id: int,
        knowledge_base_id: int,
        *,
        stream: bool = False,
    ) -> tuple[str, list]:
        # 使用配置的精排 Top K 作为最终送入 LLM 的 chunk 数
        top_k = settings.RERANK_TOP_K
        if settings.HYBRID_SEARCH_ENABLED:
            docs = search_hybrid(
                question,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                k=top_k,
            )
        else:
            docs = search_similar(
                question,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                k=top_k,
            )

        # 相邻 chunk 扩展：拉入同一文档的前后 chunk，解决跨 chunk 知识点断裂
        adjacent = get_adjacent_chunks(docs, knowledge_base_id, user_id)
        all_docs = list(docs) + adjacent

        # 按 document_id + chunk_index 排序，保持原文阅读顺序
        def _sort_key(d):
            did = d.metadata.get("document_id", "")
            idx = d.metadata.get("chunk_index", 0)
            return (str(did), int(idx) if idx is not None else 0)

        all_docs.sort(key=_sort_key)

        context = "\n\n".join([d.page_content for d in all_docs])
        if stream:
            prompt = f"""
你是企业知识库助手。

请严格基于上下文回答问题。

上下文：
{context}

问题：
{question}

请逐步回答。
"""
        else:
            prompt = f"""
你是企业知识库助手。

请严格基于上下文回答问题。

上下文：
{context}

问题：
{question}

如果上下文没有答案，请回答"未找到相关信息"。
"""
        return prompt, all_docs

    def chat(
        self,
        question: str,
        user_id: int,
        knowledge_base_id: int | None = None,
    ):
        if knowledge_base_id is None:
            answer = ask_llm(self._build_direct_prompt(question))
            return {"answer": answer, "sources": []}

        prompt, docs = self._build_rag_prompt(
            question,
            user_id,
            knowledge_base_id,
        )
        answer = ask_llm(prompt)
        return {
            "answer": answer,
            "sources": [d.page_content for d in docs],
        }

    def chat_stream(
        self,
        question: str,
        user_id: int,
        knowledge_base_id: int | None = None,
    ) -> Iterator[Union[dict, str]]:
        """流式对话。有知识库时首个事件为 {"sources": [...]}，后续为文本 chunk。"""
        if knowledge_base_id is None:
            prompt = self._build_direct_prompt(question, stream=True)
            yield from stream_llm(prompt)
        else:
            prompt, docs = self._build_rag_prompt(
                question,
                user_id,
                knowledge_base_id,
                stream=True,
            )
            yield {"sources": _extract_source_meta(docs)}
            yield from stream_llm(prompt)
