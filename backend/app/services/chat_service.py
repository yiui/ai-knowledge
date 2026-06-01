from collections.abc import Iterator

from app.core.llm import ask_llm, stream_llm
from app.services.vector_service import search_similar


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
        docs = search_similar(
            question,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            k=4,
        )
        for doc in docs:
            print("召回结果:", doc.page_content)
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
    ) -> Iterator[str]:
        if knowledge_base_id is None:
            prompt = self._build_direct_prompt(question, stream=True)
        else:
            prompt, _docs = self._build_rag_prompt(
                question,
                user_id,
                knowledge_base_id,
                stream=True,
            )
        yield from stream_llm(prompt)
