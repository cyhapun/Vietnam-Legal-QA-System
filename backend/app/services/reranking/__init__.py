"""Reranking strategies for post-retrieval passage scoring.

Implementations:
    - CrossEncoderReranker: Local fine-tuned BGE cross-encoder (local default)
    - JinaReranker: Jina AI /v1/rerank multilingual cross-encoder (cloud default)
    - HuggingFaceEmbeddingSimilarityReranker: Optional cosine similarity fallback
    - NoReranker: Pass-through strategy
"""
from app.services.reranking.base import BaseReranker
from app.services.reranking.no_reranker import NoReranker
from app.services.reranking.cross_encoder import CrossEncoderReranker
from app.services.reranking.embedding_similarity import HuggingFaceEmbeddingSimilarityReranker
from app.services.reranking.jina_reranker import JinaReranker
from app.services.reranking.fallback import FallbackReranker

__all__ = [
    "BaseReranker",
    "NoReranker",
    "CrossEncoderReranker",
    "HuggingFaceEmbeddingSimilarityReranker",
    "JinaReranker",
    "FallbackReranker",
]
