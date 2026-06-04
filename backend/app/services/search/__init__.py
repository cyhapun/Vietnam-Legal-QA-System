"""
Search Module — Strategies cho việc tìm kiếm tài liệu liên quan.

Protocol:
    BaseSearcher: Interface chung cho tất cả search strategies.

Implementations:
    - FAISSSearcher: Vector similarity search qua FAISS (mặc định)
    - BM25Searcher: Lexical search dùng BM25
    - HybridSearcher: Kết hợp vector + BM25
"""
from app.services.search.base import BaseSearcher
from app.services.search.faiss_search import FAISSSearcher
from app.services.search.bm25_search import BM25Searcher
from app.services.search.hybrid_search import HybridSearcher

__all__ = ["BaseSearcher", "FAISSSearcher", "BM25Searcher", "HybridSearcher"]
