import asyncio
from pathlib import Path

from langchain_core.documents import Document

import app.config as config_module
from app.services.pipeline import RAGPipeline
from app.services.reranking.embedding_similarity import HuggingFaceEmbeddingSimilarityReranker


def test_serverless_profile_requires_remote_embedding(monkeypatch):
    monkeypatch.setattr(config_module, "RUNTIME_PROFILE", "serverless")
    monkeypatch.setattr(config_module, "HUGGINGFACE_EMBEDDING_MODE", "api")
    monkeypatch.setattr(config_module, "EMBEDDING_MODEL", "BAAI/bge-m3")

    config_module.validate_runtime_configuration()


def test_local_profile_rejects_hub_model_id(monkeypatch):
    monkeypatch.setattr(config_module, "RUNTIME_PROFILE", "local")
    monkeypatch.setattr(config_module, "HUGGINGFACE_EMBEDDING_MODE", "local")
    monkeypatch.setattr(config_module, "EMBEDDING_MODEL", "BAAI/bge-m3")

    try:
        config_module.validate_runtime_configuration()
    except ValueError as exc:
        assert "filesystem path" in str(exc)
    else:
        raise AssertionError("local profile accepted a Hub model id")


def test_async_retrieval_dispatches_search_once():
    calls = []

    class Rewriter:
        def rewrite(self, query):
            return "legal", [query]

    class Searcher:
        strategy_name = "fake"

        async def asearch(self, queries, k, category=None, api_key=None):
            calls.append((queries, api_key))
            return [Document(page_content="text", metadata={"id": "1"})]

    class Reranker:
        strategy_name = "none"

        def rerank(self, query, documents, top_k):
            return documents[:top_k]

    class ContextBuilder:
        strategy_name = "fake"

        def build(self, docs):
            return "\n".join(doc.page_content for doc in docs)

    pipeline = RAGPipeline(Rewriter(), Searcher(), Reranker(), ContextBuilder())
    docs, context = asyncio.run(
        pipeline.aretrieve(
            "q",
            domain="legal",
            queries=["q"],
            enable_reranker=False,
            embedding_api_key="request-token",
        )
    )

    assert len(calls) == 1
    assert calls[0][1] == "request-token"
    assert len(docs) == 1
    assert context == "text"


def test_remote_reranker_uses_request_credential(monkeypatch):
    created = []

    class FakeEmbedding:
        def __init__(self, model, api_key, mode):
            created.append((model, api_key, mode))

        def embed_query(self, text):
            return [1.0, 0.0]

        def embed_documents(self, texts):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(
        "app.services.reranking.embedding_similarity.HuggingFaceEndpointEmbedding",
        FakeEmbedding,
    )
    reranker = HuggingFaceEmbeddingSimilarityReranker(
        model="BAAI/bge-m3",
        api_key="server-token",
        max_candidates=10,
    )

    reranker.rerank(
        "q",
        [Document(page_content="doc", metadata={"id": "1"})],
        top_k=1,
        api_key="request-token",
    )

    assert created == [("BAAI/bge-m3", "request-token", "api")]


def test_production_requirements_exclude_local_model_runtime():
    backend_dir = Path(__file__).resolve().parents[1]
    production = (backend_dir / "requirements.txt").read_text(encoding="utf-8").lower()
    local = (backend_dir / "requirements-local.txt").read_text(encoding="utf-8").lower()

    for package in ("torch", "transformers", "sentence-transformers", "safetensors"):
        assert package not in production
        assert package in local
