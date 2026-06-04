"""
Cross-Encoder Reranker — Dùng cross-encoder model để rerank kết quả search.
Cross-encoder cho accuracy cao hơn bi-encoder vì nó xem xét
cả query và document cùng lúc (joint encoding).
"""
from typing import List

from langchain_core.documents import Document

from app.config import HUGGINGFACE_API_KEY
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.reranking.cross_encoder")

# Default model — BGE Reranker v2 hỗ trợ multilingual (bao gồm tiếng Việt)
DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


class CrossEncoderReranker:
    """Cross-encoder reranker qua HuggingFace Inference API.

    Gọi model cross-encoder để tính relevance score cho mỗi cặp
    (query, document), rồi sắp xếp lại theo score.

    Model mặc định: BAAI/bge-reranker-v2-m3 — hỗ trợ tiếng Việt.
    """

    def __init__(
        self,
        model: str = DEFAULT_RERANKER_MODEL,
        api_key: str = HUGGINGFACE_API_KEY,
    ):
        self._model = model
        self._api_key = api_key
        self._client = None

        logger.info("CrossEncoderReranker initialized with model: %s", model)

    def _get_client(self):
        """Lazy init HuggingFace InferenceClient."""
        if self._client is None:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(
                model=self._model,
                token=self._api_key,
            )
        return self._client

    @property
    def strategy_name(self) -> str:
        return f"cross_encoder({self._model})"

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int,
    ) -> List[Document]:
        """Rerank documents bằng cross-encoder model.

        Args:
            query: Câu hỏi gốc.
            documents: Danh sách Document cần rerank.
            top_k: Số document trả về sau reranking.

        Returns:
            Top-k documents xếp theo relevance score giảm dần.
        """
        if not documents:
            return []

        client = self._get_client()

        # Tạo danh sách text pairs cho cross-encoder
        texts = [doc.page_content for doc in documents]

        try:
            # Gọi HuggingFace Inference API với task text-classification/reranking
            scores = []
            for text in texts:
                result = client.text_classification(
                    text,
                    model=self._model,
                    # Cross-encoder nhận query+document pair
                    parameters={"query": query},
                )
                # Lấy score từ kết quả (format tùy thuộc model)
                if isinstance(result, list) and len(result) > 0:
                    score = result[0].get("score", 0.0) if isinstance(result[0], dict) else float(result[0].score)
                else:
                    score = 0.0
                scores.append(score)

        except Exception as e:
            logger.warning(
                "Cross-encoder reranking thất bại, fallback về thứ tự gốc: %s",
                str(e)[:200]
            )
            return documents[:top_k]

        # Ghép score với document và sắp xếp
        scored_docs = list(zip(scores, documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = [doc for _, doc in scored_docs[:top_k]]
        logger.info(
            "CrossEncoder reranked %d → %d documents (top score: %.4f)",
            len(documents), len(results),
            scored_docs[0][0] if scored_docs else 0.0,
        )
        return results
