"""
Qdrant-backed searcher for legal clause retrieval.

This implementation uses Qdrant when available and falls back to the existing
FAISS-based retriever if the database-backed service is unavailable.
"""
from __future__ import annotations

from typing import List, Optional, Union

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

        if normalized_category.upper() in ["LKDBDS_2023", "LTTPHS_2025", "LNO_2023", "LBVMT_2020", "LXD_2014", "LDD_2024", "LCC_2024", "BLTTDS_2015"]:
            return qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="law_id",
                        match=qdrant_models.MatchValue(value=normalized_category.upper()),
                    )
                ]
            )

        return qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="category",
                    match=qdrant_models.MatchValue(value=normalized_category),
                )
            ]
        )

    def _search_qdrant(self, query: Union[str, List[str]], k: int, category: Optional[str]) -> List[Document]:
        embedding_backend = self._get_embedding_backend()
        
        try:
            from app.services.sparse_vector import SparseVectorGenerator
            sparse_generator = SparseVectorGenerator()
        except ImportError:
            sparse_generator = None

        try:
            from qdrant_client.http import models as qdrant_models
        except ImportError:  # pragma: no cover - runtime dependency check
            logger.warning("qdrant_client models import failed")
            raise

        client = self._get_client()
        query_filter = self._build_filter(category)
        
        queries = [query] if isinstance(query, str) else query
        
        prefetch = []
        for q in queries:
            query_dense_vector = embedding_backend.embed_query(q)
            prefetch.append(
                qdrant_models.Prefetch(
                    query=query_dense_vector,
                    using="text-dense",
                    limit=k * 2,
                    filter=query_filter,
                )
            )
            
            if sparse_generator:
                try:
                    query_sparse_dict = sparse_generator.generate_sparse_vector(q)
                    if query_sparse_dict and query_sparse_dict.get("indices"):
                        prefetch.append(
                            qdrant_models.Prefetch(
                                query=qdrant_models.SparseVector(
                                    indices=query_sparse_dict["indices"],
                                    values=query_sparse_dict["values"]
                                ),
                                using="text-sparse",
                                limit=k * 2,
                                filter=query_filter,
                            )
                        )
                except Exception as exc:
                    logger.warning("Sparse vector generation failed for query '%s': %s", q, exc)

        try:
            # Use query_points API with RRF fusion if multiple prefetches
            if len(prefetch) > 1:
                results = client.query_points(
                    collection_name=self._collection_name,
                    prefetch=prefetch,
                    query=qdrant_models.FusionQuery(fusion=qdrant_models.Fusion.RRF),
                    limit=k,
                    with_payload=True,
                ).points
            elif len(prefetch) == 1:
                results = client.query_points(
                    collection_name=self._collection_name,
                    query=prefetch[0].query,
                    using=prefetch[0].using,
                    limit=k,
                    query_filter=query_filter,
                    with_payload=True,
                ).points
            else:
                return []
        except AttributeError:
            # Fallback for older qdrant-client versions
            if not isinstance(query, str):
                query = query[0] if query else ""
            query_dense_vector = embedding_backend.embed_query(query)
            results = client.search(
                collection_name=self._collection_name,
                query_vector=("text-dense", query_dense_vector),
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
        query: Union[str, List[str]],
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
        query: Union[str, List[str]],
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
