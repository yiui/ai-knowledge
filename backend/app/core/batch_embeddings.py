"""按批次调用底层 embedding，兼容百炼等单次 batch ≤ 20 的 API。

含 tenacity 重试：仅对 429 / 5xx / 网络错误重试，4xx 业务错误立即抛出。
"""
import logging

from langchain_core.embeddings import Embeddings
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger("embedding")


class TransientEmbedError(Exception):
    """标记可重试的瞬时错误（429 / 5xx / 网络）。"""


def _classify_exception(exc: BaseException) -> bool:
    """判断异常是否属于瞬时错误，可重试。

    - OpenAI 兼容接口：通常有 status_code / HTTPStatus / response.status_code
    - 其他：含 'timeout' / 'connection' / '5xx' / 'rate limit' 关键字
    """
    # 显式 status code
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    if isinstance(status, int):
        if status == 429:
            return True
        if 500 <= status < 600:
            return True
        # 4xx 业务错误：除 429 外立即抛出
        return False
    # 网络类
    msg = str(exc).lower()
    transient_keywords = (
        "timeout",
        "timed out",
        "connection",
        "reset by peer",
        "rate limit",
        "temporarily",
    )
    return any(kw in msg for kw in transient_keywords)


def _call_with_retry_sync(func, *args, **kwargs):
    """对单次 embedding 调用施加 tenacity 重试。"""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        if not _classify_exception(exc):
            raise
        raise TransientEmbedError(str(exc)) from exc


class BatchEmbeddings(Embeddings):
    """按批次调用底层 embedding，兼容百炼等单次 batch ≤ 20 的 API。"""

    def __init__(
        self,
        embeddings: Embeddings,
        batch_size: int,
        max_retries: int = 4,
    ):
        self._embeddings = embeddings
        self._batch_size = max(1, batch_size)
        self._max_retries = max(1, max_retries)

    def _embed_one_batch(self, batch: list[str]) -> list[list[float]]:
        """单批 embedding，附带 tenacity 重试。

        实现要点：tenacity 的 retry_if_exception_type 只能看到装饰器内的异常。
        我们用一个内部包装函数，在 raise 前把"可重试"异常转换为 TransientEmbedError。
        """
        retrying = retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(TransientEmbedError),
            reraise=True,
        )

        @retrying
        def _call():
            try:
                return self._embeddings.embed_documents(batch)
            except Exception as exc:
                if not _classify_exception(exc):
                    raise
                # 转成 TransientEmbedError 让 tenacity 识别为可重试
                raise TransientEmbedError(str(exc)) from exc

        try:
            return _call()
        except RetryError as re:
            # tenacity 包装后重新抛出最后一次原始异常
            raise re.last_attempt.exception() from re

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            results.extend(self._embed_one_batch(batch))
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)
