"""Unit tests for unified local/cloud runtime profiles and JinaReranker."""
from __future__ import annotations

import importlib
import os
from unittest.mock import MagicMock

import httpx
import pytest
from langchain_core.documents import Document

import app.config as config_module
import app.main as main_module
from app.services.pipeline_timing import PipelineTimingCollector, reset_current_timing, set_current_timing
from app.services.reranking.jina_reranker import JinaReranker


def _reload_config(monkeypatch, env_overrides: dict[str, str | None]):
    """Reload app.config with isolated environment variables (ignoring root .env file)."""
    managed_keys = [
        "RUNTIME_PROFILE",
        "VERCEL",
        "VERCEL_ENV",
        "EMBEDDING_PROVIDER",
        "HUGGINGFACE_EMBEDDING_MODE",
        "HUGGINGFACE_EMBEDDING_MODEL",
        "EMBEDDING_MODEL",
        "PIPELINE_RERANKING",
        "RERANKER_MODEL",
        "QDRANT_COLLECTION",
        "SEMANTIC_CACHE_COLLECTION",
        "GOOGLE_API_KEYS",
        "GOOGLE_API_KEY",
        "JINA_API_KEY",
        "JINA_RERANKER_MODEL",
        "LOCAL_MODELS_PRELOAD_ENABLED",
        "LOCAL_MODELS_WARMUP_ENABLED",
        "CHAT_STORAGE_MODE",
        "NEXT_PUBLIC_CHAT_STORAGE_MODE",
    ]
    for key in managed_keys:
        monkeypatch.delenv(key, raising=False)
    for key, value in env_overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    # Prevent load_dotenv() from re-populating keys from repo .env during isolated reload
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    return importlib.reload(config_module)


@pytest.fixture(autouse=True)
def _restore_config_after_test():
    yield
    importlib.reload(config_module)


def test_local_profile_defaults(monkeypatch):
    cfg = _reload_config(monkeypatch, {"RUNTIME_PROFILE": "local"})
    cfg.validate_runtime_configuration()
    summary = cfg.runtime_profile_summary()

    assert summary["profile"] == "local"
    assert summary["embeddingProvider"] == "huggingface"
    assert summary["embeddingMode"] == "local"
    assert summary["reranking"] == "cross_encoder"
    assert summary["qdrantCollection"] == "vietlaw_clauses"
    assert summary["semanticCacheCollection"] == "semantic_cache"
    assert summary["localModelsPreload"] is True


@pytest.mark.parametrize("raw_profile", ["cloud", "serverless"])
def test_cloud_and_serverless_alias_defaults(monkeypatch, raw_profile):
    cfg = _reload_config(
        monkeypatch,
        {
            "RUNTIME_PROFILE": raw_profile,
            "GOOGLE_API_KEYS": "test-google-key",
            "JINA_API_KEY": "test-jina-key",
        },
    )
    cfg.validate_runtime_configuration()
    summary = cfg.runtime_profile_summary()

    assert summary["profile"] == "cloud"
    assert summary["embeddingProvider"] == "gemini"
    assert summary["embeddingMode"] == "api"
    assert summary["embeddingModel"] == "models/gemini-embedding-001"
    assert summary["reranking"] == "jina"
    assert summary["rerankerModel"] == "jina-reranker-v2-base-multilingual"
    assert summary["qdrantCollection"] == "vietlaw_clauses_gemini"
    assert summary["semanticCacheCollection"] == "semantic_cache_gemini"
    assert summary["localModelsPreload"] is False


def test_cloud_profile_requires_jina_key_when_jina_reranker_active(monkeypatch):
    cfg = _reload_config(
        monkeypatch,
        {
            "RUNTIME_PROFILE": "cloud",
            "GOOGLE_API_KEYS": "test-google-key",
        },
    )
    with pytest.raises(ValueError, match="JINA_API_KEY"):
        cfg.validate_runtime_configuration()


def test_cloud_profile_rejects_local_cross_encoder(monkeypatch):
    cfg = _reload_config(
        monkeypatch,
        {
            "RUNTIME_PROFILE": "cloud",
            "GOOGLE_API_KEYS": "test-google-key",
            "PIPELINE_RERANKING": "cross_encoder",
        },
    )
    with pytest.raises(ValueError, match="cross_encoder"):
        cfg.validate_runtime_configuration()


def test_invalid_runtime_profile_raises(monkeypatch):
    cfg = _reload_config(monkeypatch, {"RUNTIME_PROFILE": "unknown_mode"})
    with pytest.raises(ValueError, match="RUNTIME_PROFILE"):
        cfg.validate_runtime_configuration()


def test_jina_reranker_preserves_metadata_and_orders_by_score(monkeypatch):
    captured = {}

    class DummyResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return {
                "model": "jina-reranker-v2-base-multilingual",
                "results": [
                    {"index": 2, "relevance_score": 0.94},
                    {"index": 0, "relevance_score": 0.61},
                ],
            }

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return DummyResponse()

    monkeypatch.setattr(httpx, "Client", DummyClient)

    docs = [
        Document(page_content="Điều 1 về dân sự", metadata={"law_id": "BLDS", "article": "1"}),
        Document(page_content="Điều 2 về hình sự", metadata={"law_id": "BLHS", "article": "2"}),
        Document(page_content="Điều 3 về công chứng đất đai", metadata={"law_id": "LDD", "article": "3"}),
    ]
    reranker = JinaReranker(api_key="jina_secret_key", max_candidates=10, fail_open=False)

    collector = PipelineTimingCollector(request_id="req-1", endpoint="/chat", streaming=False, enabled=True)
    token = set_current_timing(collector)
    try:
        ranked = reranker.rerank("công chứng hợp đồng đất đai", docs, top_k=2)
    finally:
        reset_current_timing(token)

    assert captured["json"]["return_documents"] is False
    assert captured["json"]["top_n"] == 2
    assert captured["headers"]["Authorization"] == "Bearer jina_secret_key"
    assert [doc.metadata["law_id"] for doc in ranked] == ["LDD", "BLDS"]
    assert ranked[0].metadata["rerank_score"] == pytest.approx(0.94)
    assert "reranking" in collector.payload("ok")["durations_ms"]


def test_jina_reranker_rotates_keys_on_429(monkeypatch):
    used_auth_headers = []

    class DummyResponse:
        def __init__(self, code: int, body: dict | None = None):
            self.status_code = code
            self._body = body or {}
            self.text = str(body or "")

        def json(self):
            return self._body

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            used_auth_headers.append(headers["Authorization"])
            if len(used_auth_headers) == 1:
                return DummyResponse(429)
            return DummyResponse(
                200,
                {"results": [{"index": 1, "relevance_score": 0.88}]},
            )

    monkeypatch.setattr(httpx, "Client", DummyClient)
    monkeypatch.setattr("app.services.reranking.jina_reranker.time.sleep", lambda _: None)

    docs = [
        Document(page_content="Doc A", metadata={"id": "A"}),
        Document(page_content="Doc B", metadata={"id": "B"}),
    ]
    reranker = JinaReranker(api_key="key_one,key_two", fail_open=False)
    ranked = reranker.rerank("query", docs, top_k=1)

    assert used_auth_headers == ["Bearer key_one", "Bearer key_two"]
    assert ranked[0].metadata["id"] == "B"


def test_jina_reranker_fail_open_and_strict_modes(monkeypatch):
    class FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx, "Client", FailingClient)
    monkeypatch.setattr("app.services.reranking.jina_reranker.time.sleep", lambda _: None)

    docs = [
        Document(page_content="First", metadata={"id": "1"}),
        Document(page_content="Second", metadata={"id": "2"}),
    ]

    open_reranker = JinaReranker(api_key="secret_xyz", fail_open=True)
    fallback_docs = open_reranker.rerank("query", docs, top_k=1)
    assert [d.metadata["id"] for d in fallback_docs] == ["1"]

    strict_reranker = JinaReranker(api_key="secret_xyz", fail_open=False)
    with pytest.raises(RuntimeError) as exc_info:
        strict_reranker.rerank("query", docs, top_k=1)
    assert "secret_xyz" not in str(exc_info.value)


def test_jina_reranker_empty_short_circuit(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(httpx, "Client", mock_client)
    reranker = JinaReranker(api_key="any-key", fail_open=False)

    assert reranker.rerank("query", [], top_k=5) == []
    assert reranker.rerank("query", [Document(page_content="x")], top_k=0) == []
    mock_client.assert_not_called()


def test_check_artifacts_in_cloud_mode(monkeypatch):
    monkeypatch.setattr(main_module, "validate_runtime_configuration", lambda: None)
    monkeypatch.setattr(main_module, "RUNTIME_PROFILE", "cloud")
    monkeypatch.setattr(main_module, "EMBEDDING_PROVIDER", "gemini")
    monkeypatch.setattr(main_module, "EMBEDDING_MODEL", "models/gemini-embedding-001")
    monkeypatch.setattr(main_module, "GOOGLE_API_KEYS", "test-key")
    monkeypatch.setattr(main_module, "JINA_API_KEY", "test-jina")
    monkeypatch.setattr(
        main_module,
        "PIPELINE_CONFIG",
        {"reranking": "jina", "reranker_model": "jina-reranker-v2-base-multilingual"},
    )

    artifacts = main_module._check_artifacts()
    assert artifacts["embedding"]["status"] == "ok"
    assert artifacts["embedding"]["provider"] == "gemini"
    assert artifacts["embedding"]["mode"] == "api"
    assert artifacts["embedding"]["weights"] is False
    assert artifacts["reranker"]["status"] == "ok"
    assert artifacts["reranker"]["provider"] == "jina"
    assert artifacts["reranker"]["mode"] == "api"
    assert artifacts["reranker"]["weights"] is False
