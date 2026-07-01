from typing import Protocol


class RerankClient(Protocol):
    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[tuple[int, float]]:
        """返回 (原始文档索引, 相关性分数)，按分数降序。"""
