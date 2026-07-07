import logging
from typing import List
from app.services.reranking.base import BaseReranker

logger = logging.getLogger(__name__)

class FallbackReranker(BaseReranker):
    """
    Wrapper để tự động fallback sang mô hình reranker dự phòng nếu mô hình chính bị lỗi.
    Ví dụ: Lỗi OutOfMemory từ CrossEncoder -> Fallback về NoReranker.
    """
    def __init__(self, primary: BaseReranker, secondary: BaseReranker):
        self.primary = primary
        self.secondary = secondary

    def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[str]:
        try:
            return self.primary.rerank(query, documents, top_n)
        except Exception as e:
            logger.warning(f"Primary reranker failed ({e}). Fallback to secondary...")
            try:
                return self.secondary.rerank(query, documents, top_n)
            except Exception as e2:
                logger.error(f"Both primary and secondary rerankers failed. Errors: {e} | {e2}")
                raise RuntimeError("All reranker providers failed.") from e2
