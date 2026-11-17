"""
Reranking Module — Strategies cho việc xếp hạng lại kết quả search.

Protocol:
    BaseReranker: Interface chung cho tất cả reranking strategies.

Implementations:
    - NoReranker: Pass-through (không rerank, giữ nguyên thứ tự)
    - CrossEncoderReranker: Dùng cross-encoder model cục bộ để rerank
    - JinaReranker: Dùng Jina AI Cross-Encoder REST API (/v1/rerank) cho mode cloud
    - HuggingFaceEmbeddingSimilarityReranker: Cosine similarity qua embedding API
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
