"""
BM25 Search — Lexical search dùng thuật toán BM25 (Okapi BM25).
Tìm kiếm dựa trên exact keyword matching, bổ sung cho vector search.
"""
import re
from typing import List, Optional

from langchain_core.documents import Document

from app.config import RETRIEVER_K
from app.services.knowledge_base import document_matches_category
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.search.bm25")


def _simple_tokenize(text: str) -> List[str]:
    """Tokenize đơn giản cho tiếng Việt — tách theo khoảng trắng và ký tự đặc biệt."""
    text = text.lower().strip()
    tokens = re.findall(r'\w+', text, re.UNICODE)
    return tokens


class BM25Searcher:
    """BM25 lexical search — tìm kiếm dựa trên keyword matching.

    Hữu ích cho các truy vấn chứa thuật ngữ pháp lý cụ thể
    mà vector search có thể bỏ sót do semantic gap.

    Lưu ý: Cần gọi build_index() trước khi search.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self._k1 = k1
        self._b = b
        self._documents: List[Document] = []
        self._corpus_tokens: List[List[str]] = []
        self._doc_lengths: List[int] = []
        self._avg_doc_length: float = 0.0
        self._df: dict = {}  # document frequency cho mỗi term
        self._n_docs: int = 0
        self._indexed = False

    @property
    def strategy_name(self) -> str:
        return "bm25"

    def build_index(self, documents: List[Document]) -> None:
        """Xây dựng BM25 index từ danh sách Document.

        Args:
            documents: Danh sách Document đã chunked.
        """
        self._documents = documents
        self._n_docs = len(documents)
        self._corpus_tokens = []
        self._doc_lengths = []
        self._df = {}

        for doc in documents:
            tokens = _simple_tokenize(doc.page_content)
            self._corpus_tokens.append(tokens)
            self._doc_lengths.append(len(tokens))

            # Đếm document frequency (mỗi term chỉ đếm 1 lần per doc)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self._df[token] = self._df.get(token, 0) + 1

        self._avg_doc_length = (
            sum(self._doc_lengths) / self._n_docs if self._n_docs > 0 else 0.0
        )
        self._indexed = True
        logger.info("BM25 index built: %d documents, %d unique terms", self._n_docs, len(self._df))

    def _score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        """Tính BM25 score cho một document."""
        import math

        score = 0.0
        doc_tokens = self._corpus_tokens[doc_idx]
        doc_len = self._doc_lengths[doc_idx]

        # Đếm term frequency trong document
        tf_map = {}
        for token in doc_tokens:
            tf_map[token] = tf_map.get(token, 0) + 1

        for term in query_tokens:
            if term not in self._df:
                continue

            df = self._df[term]
            tf = tf_map.get(term, 0)

            # IDF component
            idf = math.log((self._n_docs - df + 0.5) / (df + 0.5) + 1.0)

            # TF component with length normalization
            tf_norm = (tf * (self._k1 + 1)) / (
                tf + self._k1 * (1 - self._b + self._b * doc_len / self._avg_doc_length)
            )

            score += idf * tf_norm

        return score

    def search(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Tìm kiếm bằng BM25."""
        if not self._indexed:
            logger.warning("BM25 index chưa được build! Trả về danh sách rỗng.")
            return []

        query_tokens = _simple_tokenize(query)

        # Tính score cho tất cả documents
        scored = []
        for idx in range(self._n_docs):
            doc = self._documents[idx]

            # Lọc theo category nếu có
            if not document_matches_category(doc.metadata, category):
                continue

            score = self._score_document(query_tokens, idx)
            if score > 0:
                scored.append((score, idx))

        # Sắp xếp theo score giảm dần và lấy top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [self._documents[idx] for _, idx in scored[:k]]

        logger.info("BM25 search: query='%s' → %d results", query[:50], len(results))
        return results

    async def asearch(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Async version — BM25 chạy in-memory nên gọi sync cũng nhanh."""
        return self.search(query, k=k, category=category)
