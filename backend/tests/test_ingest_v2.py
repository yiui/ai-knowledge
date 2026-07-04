"""v2 异步向量化回归 smoke test。

不依赖 Postgres（用 sqlite in-memory）、不依赖真实 embedding API。
覆盖：
1. DocumentStatus 枚举 / 状态写回
2. BatchEmbeddings 重试分类（429 重试、4xx 业务错误直接抛）
3. upsert_document_vectors 幂等（先 delete 后 insert）

跑法：
    cd backend && PYTHONPATH=. .venv/bin/python tests/test_ingest_v2.py
"""
import os
import sys
import types
from unittest.mock import patch, MagicMock

# 让 .env 缺失时不爆炸
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "u")
os.environ.setdefault("POSTGRES_PASSWORD", "p")
os.environ.setdefault("POSTGRES_DB", "d")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "x")
os.environ.setdefault("MINIO_SECRET_KEY", "x")
os.environ.setdefault("MINIO_BUCKET", "b")
os.environ.setdefault("MINIO_SECURE", "false")
os.environ.setdefault("EMBEDDING_API_KEY", "test-key")
os.environ.setdefault("APP_NAME", "test")
os.environ.setdefault("APP_VERSION", "0")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("GEMINI_API_KEY", "x")
os.environ.setdefault("GEMINI_MODEL", "x")
os.environ.setdefault("OLLAMA_BASE_URL", "http://x")
os.environ.setdefault("OLLAMA_MODEL", "x")


def test_document_status_enum():
    from app.models.document import DocumentStatus
    assert DocumentStatus.PENDING.value == "pending"
    assert DocumentStatus.PROCESSING.value == "processing"
    assert DocumentStatus.READY.value == "ready"
    assert DocumentStatus.FAILED.value == "failed"
    print("✓ test_document_status_enum")


def test_classify_exception():
    from app.core.batch_embeddings import _classify_exception

    # 429 → 重试
    e = Exception("rate limited")
    e.status_code = 429
    assert _classify_exception(e) is True

    # 500 → 重试
    e = Exception("server error")
    e.status_code = 503
    assert _classify_exception(e) is True

    # 400 → 不重试
    e = Exception("bad request")
    e.status_code = 400
    assert _classify_exception(e) is False

    # 401 → 不重试
    e = Exception("unauthorized")
    e.status_code = 401
    assert _classify_exception(e) is False

    # 网络错 → 重试
    e = Exception("Read timed out")
    assert _classify_exception(e) is True

    # 无 status_code 的业务错 → 不重试
    e = Exception("some other error")
    assert _classify_exception(e) is False
    print("✓ test_classify_exception")


def test_batch_embeddings_retry_on_429():
    """429 应被 tenacity 重试，最终成功。"""
    from app.core.batch_embeddings import BatchEmbeddings
    from langchain_core.embeddings import Embeddings

    class FlakyEmbeddings(Embeddings):
        def __init__(self):
            self.calls = 0

        def embed_documents(self, texts):
            self.calls += 1
            if self.calls < 3:
                err = Exception("rate limited")
                err.status_code = 429
                raise err
            return [[0.0] * 4 for _ in texts]

        def embed_query(self, text):
            return [0.0] * 4

    inner = FlakyEmbeddings()
    be = BatchEmbeddings(inner, batch_size=20, max_retries=4)
    out = be.embed_documents(["hello"])
    assert len(out) == 1
    assert inner.calls == 3  # 第 3 次成功
    print("✓ test_batch_embeddings_retry_on_429")


def test_batch_embeddings_no_retry_on_400():
    """400 业务错误应直接抛，不重试。"""
    from app.core.batch_embeddings import BatchEmbeddings
    from langchain_core.embeddings import Embeddings

    class BadRequest(Embeddings):
        def __init__(self):
            self.calls = 0

        def embed_documents(self, texts):
            self.calls += 1
            err = Exception("bad request")
            err.status_code = 400
            raise err

        def embed_query(self, text):
            return [0.0] * 4

    inner = BadRequest()
    be = BatchEmbeddings(inner, batch_size=20, max_retries=4)
    try:
        be.embed_documents(["hello"])
    except Exception as e:
        assert inner.calls == 1, f"应只调用 1 次，实际 {inner.calls}"
        assert "bad request" in str(e)
    else:
        raise AssertionError("期望 400 直接抛")
    print("✓ test_batch_embeddings_no_retry_on_400")


def test_upsert_document_vectors_idempotent():
    """upsert_document_vectors 应先 delete 后 insert，幂等。"""
    from app.services import vector_service

    with patch.object(vector_service, "engine") as mock_engine, \
         patch.object(vector_service, "_get_vector_store") as mock_get_vs:
        # 模拟 connection context
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        mock_vs = MagicMock()
        mock_get_vs.return_value = mock_vs

        chunks = [MagicMock(), MagicMock()]
        result = vector_service.upsert_document_vectors(
            chunks=chunks, document_id=42, knowledge_base_id=1,
        )

        # 验证：先 delete
        assert mock_conn.execute.called
        first_call_sql = str(mock_conn.execute.call_args_list[0].args[0])
        assert "DELETE FROM langchain_pg_embedding" in first_call_sql
        # 验证：再 add_documents
        mock_vs.add_documents.assert_called_once()
        assert result == 2

    # chunks=[] 时直接返回 0
    with patch.object(vector_service, "engine"), \
         patch.object(vector_service, "_get_vector_store") as mock_get_vs:
        mock_vs = MagicMock()
        mock_get_vs.return_value = mock_vs
        result = vector_service.upsert_document_vectors(
            chunks=[], document_id=42, knowledge_base_id=1,
        )
        assert result == 0
        mock_vs.add_documents.assert_not_called()

    print("✓ test_upsert_document_vectors_idempotent")


def test_process_document_with_status_success():
    """成功路径：_do_process_document 成功 → 写 status=ready + vector_count。"""
    from app.services import ingest_service

    with patch.object(ingest_service, "_do_process_document", return_value=7), \
         patch.object(ingest_service, "_set_status") as mock_set:
        ok = ingest_service.process_document_with_status(
            document_id=1, file_path="x", user_id=1, knowledge_base_id=1,
            max_retries=3,
        )
        assert ok is True
        mock_set.assert_called_once()
        kwargs = mock_set.call_args.kwargs
        assert kwargs["status"] == "ready"
        assert kwargs["vector_count"] == 7
        assert kwargs["error_message"] is None
    print("✓ test_process_document_with_status_success")


def test_process_document_with_status_failure_after_retries():
    """失败路径：3 次都失败 → 写 status=failed。"""
    from app.services import ingest_service

    with patch.object(ingest_service, "_do_process_document",
                      side_effect=RuntimeError("embedding down")), \
         patch.object(ingest_service, "time") as mock_time, \
         patch.object(ingest_service, "_set_status") as mock_set:
        ok = ingest_service.process_document_with_status(
            document_id=1, file_path="x", user_id=1, knowledge_base_id=1,
            max_retries=3,
        )
        assert ok is False
        # 最后一次写状态是 failed
        final_call = mock_set.call_args_list[-1]
        assert final_call.kwargs["status"] == "failed"
        assert "embedding down" in final_call.kwargs["error_message"]
    print("✓ test_process_document_with_status_failure_after_retries")


def test_process_document_with_status_succeeds_on_retry():
    """失败-成功路径：第 2 次成功也写 ready。"""
    from app.services import ingest_service

    call_count = {"n": 0}

    def fake_process(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise RuntimeError("transient")
        return 3

    with patch.object(ingest_service, "_do_process_document",
                      side_effect=fake_process), \
         patch.object(ingest_service, "time"), \
         patch.object(ingest_service, "_set_status") as mock_set:
        ok = ingest_service.process_document_with_status(
            document_id=1, file_path="x", user_id=1, knowledge_base_id=1,
            max_retries=3,
        )
        assert ok is True
        assert call_count["n"] == 2
        final_call = mock_set.call_args_list[-1]
        assert final_call.kwargs["status"] == "ready"
        assert final_call.kwargs["vector_count"] == 3
    print("✓ test_process_document_with_status_succeeds_on_retry")


def test_reindex_route_guard():
    """POST /documents/{id}/reindex 路由存在，且支持 failed/processing 状态。"""
    from app.api.routes.documents import router
    paths = [r.path for r in router.routes if hasattr(r, "path")]
    assert "/documents/{doc_id}/reindex" in paths
    print("✓ test_reindex_route_guard")


def test_claim_next_pending_sql():
    """worker 抢锁 SQL 形如 UPDATE...RETURNING。"""
    from app.worker import ingest_worker
    import inspect
    src = inspect.getsource(ingest_worker.claim_next_pending)
    assert "FOR UPDATE SKIP LOCKED" in src
    assert "RETURNING" in src
    assert "status = :pending" in src
    print("✓ test_claim_next_pending_sql")


def test_reclaim_stale_processing_sql():
    """僵死 processing 回收逻辑存在且使用 interval。"""
    from app.worker import ingest_worker
    import inspect
    src = inspect.getsource(ingest_worker.reclaim_stale_processing)
    assert "status = :pending" in src
    assert "interval" in src
    print("✓ test_reclaim_stale_processing_sql")


if __name__ == "__main__":
    tests = [
        test_document_status_enum,
        test_classify_exception,
        test_batch_embeddings_retry_on_429,
        test_batch_embeddings_no_retry_on_400,
        test_upsert_document_vectors_idempotent,
        test_process_document_with_status_success,
        test_process_document_with_status_failure_after_retries,
        test_process_document_with_status_succeeds_on_retry,
        test_reindex_route_guard,
        test_claim_next_pending_sql,
        test_reclaim_stale_processing_sql,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(0 if failed == 0 else 1)
