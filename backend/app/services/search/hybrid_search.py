"""
Hybrid Search — Kết hợp Vector Search (FAISS) + Lexical Search (BM25).
Sử dụng Reciprocal Rank Fusion (RRF) để merge kết quả từ hai nguồn.
"""
from typing import List, Optional, Dict

from langchain_core.documents import Document

from app.config import RETRIEVER_K
from app.services.search.faiss_search import FAISSSearcher
from app.services.search.bm25_search import BM25Searcher
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.search.hybrid")


class HybridSearcher:
    """Hybrid Search = Vector (FAISS) + Lexical (BM25) với RRF fusion.

    Kết hợp ưu điểm của cả hai phương pháp:
    - Vector search: Tìm được documents có semantic similarity cao
    - BM25: Bắt được exact keyword matches mà vector search bỏ sót

    Reciprocal Rank Fusion (RRF) được dùng để merge kết quả
    vì nó robust và không cần normalize scores giữa hai hệ thống.
    """

    def __init__(
        self,
        vector_searcher: FAISSSearcher,
        bm25_searcher: BM25Searcher,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        rrf_k: int = 60,
    ):
        """
        Args:
            vector_searcher: FAISS vector search component.
            bm25_searcher: BM25 lexical search component.
            vector_weight: Trọng số cho vector search results.
            bm25_weight: Trọng số cho BM25 results.
            rrf_k: Hằng số k trong công thức RRF (mặc định = 60).
        """
        self._vector_searcher = vector_searcher
        self._bm25_searcher = bm25_searcher
        self._vector_weight = vector_weight
        self._bm25_weight = bm25_weight
        self._rrf_k = rrf_k

    @property
    def strategy_name(self) -> str:
        return f"hybrid(vector={self._vector_weight},bm25={self._bm25_weight})"

    def _rrf_fuse(
        self,
        vector_docs: List[Document],
        bm25_docs: List[Document],
        k: int,
    ) -> List[Document]:
        """Merge kết quả bằng Reciprocal Rank Fusion.

        RRF Score = Σ weight / (rrf_k + rank)
        """
        # Map từ document ID → (Document, RRF score)
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        # Score từ vector search
        for rank, doc in enumerate(vector_docs):
            doc_id = doc.metadata.get("id", str(rank))
            rrf_score = self._vector_weight / (self._rrf_k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score
            doc_map[doc_id] = doc

        # Score từ BM25
        for rank, doc in enumerate(bm25_docs):
            doc_id = doc.metadata.get("id", f"bm25_{rank}")
            rrf_score = self._bm25_weight / (self._rrf_k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Sắp xếp theo tổng RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = [doc_map[doc_id] for doc_id in sorted_ids[:k]]

        logger.info(
            "Hybrid RRF fusion: %d vector + %d bm25 → %d merged results",
            len(vector_docs), len(bm25_docs), len(results),
        )
        return results

    def search(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Hybrid search: gọi cả vector và BM25, rồi merge bằng RRF."""
        # Lấy nhiều hơn k từ mỗi nguồn để RRF có nhiều dữ liệu hơn
        fetch_k = k * 2

        vector_docs = self._vector_searcher.search(query, k=fetch_k, category=category)
        bm25_docs = self._bm25_searcher.search(query, k=fetch_k, category=category)

        return self._rrf_fuse(vector_docs, bm25_docs, k=k)

    async def asearch(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Async hybrid search."""
        fetch_k = k * 2

        vector_docs = await self._vector_searcher.asearch(query, k=fetch_k, category=category)
        bm25_docs = await self._bm25_searcher.asearch(query, k=fetch_k, category=category)

        return self._rrf_fuse(vector_docs, bm25_docs, k=k)
