"""
Qdrant-backed searcher for legal clause retrieval.

This implementation uses Qdrant when available and falls back to the existing
FAISS-based retriever if the database-backed service is unavailable.
"""
from __future__ import annotations

from typing import List, Optional

from langchain_core.documents import Document

from app.config import (
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_URL,
    RETRIEVER_K,
)
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.services.embedding.ollama import OllamaEmbedding
from app.services.knowledge_base import (
    ALL_LAWS_CATEGORY,
    document_matches_category,
    normalize_category,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.search.qdrant")


class QdrantSearcher:
    """Vector search using Qdrant with a FAISS fallback for local resilience."""

    def __init__(
        self,
        vectorstore,
        fallback_searcher=None,
        collection_name: str = QDRANT_COLLECTION,
    ):
        self._vectorstore = vectorstore
        self._fallback_searcher = fallback_searcher
        self._collection_name = collection_name
        self._client = None

    @property
    def strategy_name(self) -> str:
        return "qdrant"

    def _get_embedding_backend(self):
        from app.config import EMBEDDING_PROVIDER

        if EMBEDDING_PROVIDER == "ollama":
            return OllamaEmbedding()
        return HuggingFaceEndpointEmbedding()

    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError as exc:  # pragma: no cover - runtime dependency check
                raise RuntimeError("qdrant-client is not installed") from exc

            self._client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        return self._client

    def _build_filter(self, category: Optional[str]):
        normalized_category = normalize_category(category)
        if normalized_category == ALL_LAWS_CATEGORY:
            return None

        try:
            from qdrant_client.http import models as qdrant_models
        except ImportError:  # pragma: no cover - runtime dependency check
            return None

        return qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="category",
                    match=qdrant_models.MatchValue(value=normalized_category),
                )
            ]
        )

    def _search_qdrant(self, query: str, k: int, category: Optional[str]) -> List[Document]:
        embedding_backend = self._get_embedding_backend()
        query_vector = embedding_backend.embed_query(query)

        try:
            from qdrant_client.http import models as qdrant_models
        except ImportError:  # pragma: no cover - runtime dependency check
            logger.warning("qdrant_client models import failed")
            raise

        client = self._get_client()
        query_filter = self._build_filter(category)

        try:
            # Use query_points API for newer qdrant-client versions
            results = client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                limit=k,
                query_filter=query_filter,
                with_payload=True,
            ).points
        except AttributeError:
            # Fallback for older qdrant-client versions that have search() method
            results = client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=k,
                query_filter=query_filter,
                with_payload=True,
            )

        documents: List[Document] = []
        for point in results:
            payload = point.payload or {}
            metadata = {
                "id": payload.get("id", point.id),
                "law_id": payload.get("law_id"),
                "category": payload.get("category"),
            }
            documents.append(
                Document(page_content=payload.get("content", ""), metadata=metadata)
            )
        return documents

    def search(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        try:
            return self._search_qdrant(query, k=k, category=category)
        except Exception as exc:
            logger.warning("Qdrant retrieval failed, falling back to FAISS: %s", exc)
            if self._fallback_searcher is not None:
                return self._fallback_searcher.search(query, k=k, category=category)
            return []

    async def asearch(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        import asyncio
        try:
            return await asyncio.to_thread(self._search_qdrant, query, k, category)
        except Exception as exc:
            logger.warning("Qdrant async retrieval failed, falling back to fallback searcher: %s", exc)
            if self._fallback_searcher is not None:
                if hasattr(self._fallback_searcher, "asearch"):
                    return await self._fallback_searcher.asearch(query, k=k, category=category)
                return self._fallback_searcher.search(query, k=k, category=category)
            return []
