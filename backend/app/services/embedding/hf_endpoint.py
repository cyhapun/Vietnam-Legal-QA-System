"""
HuggingFace Endpoint Embedding — gọi HuggingFace Inference API.
Đây là implementation mặc định, wrap lại HuggingFaceEndpointEmbeddings
từ langchain_huggingface nhưng tuân thủ BaseEmbedding protocol.
"""
from typing import List

from langchain_huggingface import HuggingFaceEndpointEmbeddings, HuggingFaceEmbeddings

from app.config import HUGGINGFACE_API_KEY, EMBEDDING_MODEL, HUGGINGFACE_EMBEDDING_MODE
from app.services.embedding.errors import EmbeddingAuthError, EmbeddingServerError
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.embedding.hf_endpoint")


def _raise_huggingface_error(exc: Exception) -> None:
    detail = str(exc)
    if "401" in detail or "Unauthorized" in detail or "Invalid username or password" in detail:
        raise EmbeddingAuthError(
            "API Key HuggingFace khong hop le, da het han, hoac khong co quyen dung embedding BAAI/bge-m3. "
            "Vui long kiem tra lai HuggingFace API key trong phan cau hinh."
        ) from exc

    if "500" in detail or "Internal Server Error" in detail or "Server error" in detail:
        raise EmbeddingServerError(
            "Dich vu HuggingFace embedding dang loi phia may chu khi goi BAAI/bge-m3. "
            "Vui long thu lai sau hoac chon cau hinh embedding on dinh hon."
        ) from exc

    raise EmbeddingServerError(
        f"Khong the tao embedding bang HuggingFace BAAI/bge-m3: {detail}"
    ) from exc


class HuggingFaceEndpointEmbedding:
    """Embedding qua HuggingFace Inference API.

    Wrap langchain HuggingFaceEndpointEmbeddings để phù hợp
    với BaseEmbedding protocol và có thể swap trong pipeline.
    """

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        api_key: str = None,
        mode: str = HUGGINGFACE_EMBEDDING_MODE,
    ):
        self._model_name = model
        self._mode = mode
        
        if mode == "api":
            final_api_key = api_key or HUGGINGFACE_API_KEY
            if not final_api_key:
                raise EmbeddingAuthError(
                    "Vui lòng cung cấp API Key HuggingFace trong cấu hình để sử dụng mô hình Embedding qua API."
                )
            logger.info("Đang kết nối mô hình %s qua Hugging Face API...", model)
            self._engine = HuggingFaceEndpointEmbeddings(
                model=model,
                task="feature-extraction",
                huggingfacehub_api_token=final_api_key,
            )
        else:
            logger.info("Đang tải mô hình %s chạy TRỰC TIẾP (Local) qua sentence-transformers...", model)
            self._engine = HuggingFaceEmbeddings(
                model_name=model,
                # Tự động dùng GPU nếu có, nếu không thì CPU
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def langchain_embeddings(self):
        """Trả về object langchain gốc — cần thiết cho FAISS compatibility."""
        return self._engine

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Nhúng nhiều văn bản cùng lúc."""
        try:
            return self._engine.embed_documents(texts)
        except Exception as exc:
            _raise_huggingface_error(exc)

    def embed_query(self, text: str) -> List[float]:
        """Nhúng một câu truy vấn."""
        try:
            return self._engine.embed_query(text)
        except Exception as exc:
            _raise_huggingface_error(exc)
