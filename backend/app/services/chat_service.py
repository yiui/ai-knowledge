from collections.abc import Iterator

from app.core.llm import ask_llm, stream_llm
from app.services.vector_service import search_similar


class ChatService:

    def _build_prompt(self, question: str, user_id: int, *, stream: bool = False) -> tuple[str, list]:
        docs = search_similar(question, user_id=user_id, k=4)
        context = "\n\n".join([d.page_content for d in docs])
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

如果上下文没有答案，请回答“未找到相关信息”。
"""
        return prompt, docs

    def chat(self, question: str, user_id: int):
        prompt, docs = self._build_prompt(question, user_id)
        answer = ask_llm(prompt)

        return {
            "answer": answer,
            "sources": [d.page_content for d in docs],
        }

    def chat_stream(self, question: str, user_id: int) -> Iterator[str]:
        prompt, _docs = self._build_prompt(question, user_id, stream=True)
        yield from stream_llm(prompt)
