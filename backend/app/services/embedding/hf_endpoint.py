"""
HuggingFace Endpoint Embedding — gọi HuggingFace Inference API.
Đây là implementation mặc định, wrap lại HuggingFaceEndpointEmbeddings
từ langchain_huggingface nhưng tuân thủ BaseEmbedding protocol.
"""
from typing import List

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.config import HUGGINGFACE_API_KEY, EMBEDDING_MODEL
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.embedding.hf_endpoint")


class HuggingFaceEndpointEmbedding:
    """Embedding qua HuggingFace Inference API.

    Wrap langchain HuggingFaceEndpointEmbeddings để phù hợp
    với BaseEmbedding protocol và có thể swap trong pipeline.
    """

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        api_key: str = HUGGINGFACE_API_KEY,
    ):
        if not api_key:
            raise ValueError(
                "Không tìm thấy HUGGINGFACE_API_KEY. "
                "Vui lòng kiểm tra lại file .env của bạn nhé."
            )

        self._model_name = model
        logger.info("Đang kết nối mô hình %s qua Hugging Face API...", model)

        self._engine = HuggingFaceEndpointEmbeddings(
            model=model,
            task="feature-extraction",
            huggingfacehub_api_token=api_key,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def langchain_embeddings(self) -> HuggingFaceEndpointEmbeddings:
        """Trả về object langchain gốc — cần thiết cho FAISS compatibility."""
        return self._engine

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Nhúng nhiều văn bản cùng lúc."""
        return self._engine.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Nhúng một câu truy vấn."""
        return self._engine.embed_query(text)
