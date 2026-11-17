"""
Google Gemini Embedding Adapter.
Sử dụng REST API của Google AI Studio (models/gemini-embedding-001) với vector 1024 chiều.
Hỗ trợ batching, phân tách taskType (RETRIEVAL_DOCUMENT vs RETRIEVAL_QUERY) và xoay vòng API Keys.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import List, Optional
import httpx

from app.config import (
    GOOGLE_API_KEYS,
)
from app.services.embedding.errors import (
    EmbeddingAuthError,
    EmbeddingServerError,
    EmbeddingServiceError,
)
from app.services.pipeline_timing import current_timing
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.embedding.gemini")

DEFAULT_GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"
DEFAULT_DIMENSION = 1024
DEFAULT_BATCH_SIZE = 100
GOOGLE_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _parse_keys(keys_input: Optional[List[str] | str] = None) -> List[str]:
    """Phân giải danh sách API keys từ input hoặc config."""
    if isinstance(keys_input, list):
        keys = [k.strip() for k in keys_input if k and k.strip()]
        if keys:
            return keys

    raw = keys_input or GOOGLE_API_KEYS or ""
    keys: List[str] = []
    for part in str(raw).split(","):
        cleaned = part.strip()
        if cleaned and cleaned not in keys:
            keys.append(cleaned)
    return keys


class GeminiEmbedding:
    """Embedding adapter kết nối Google AI Studio (gemini-embedding-001)."""

    def __init__(
        self,
        model: str = DEFAULT_GEMINI_EMBEDDING_MODEL,
        api_keys: Optional[List[str] | str] = None,
        dimension: int = DEFAULT_DIMENSION,
        batch_size: int = DEFAULT_BATCH_SIZE,
        timeout: float = 30.0,
    ):
        self._model = model if model.startswith("models/") else f"models/{model}"
        self._dimension = dimension
        self._batch_size = max(1, min(batch_size, 100))
        self._timeout = timeout
        self._keys = _parse_keys(api_keys)
        self._key_index = 0
        self._lock = threading.Lock()

        if not self._keys:
            raise EmbeddingAuthError(
                "Không tìm thấy Google API Key. Vui lòng thiết lập biến GOOGLE_API_KEYS trong cấu hình."
            )

        logger.info(
            "Khởi tạo GeminiEmbedding: model=%s, dimension=%d, keys_count=%d",
            self._model,
            self._dimension,
            len(self._keys),
        )

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def langchain_embeddings(self):
        """Tương thích với các component LangChain/FAISS."""
        return self

    def _get_current_key(self) -> str:
        with self._lock:
            return self._keys[self._key_index % len(self._keys)]

    def _rotate_key(self, failed_key: str) -> str:
        with self._lock:
            if self._keys[self._key_index % len(self._keys)] == failed_key:
                self._key_index = (self._key_index + 1) % len(self._keys)
                next_key = self._keys[self._key_index]
                logger.warning(
                    "Đã xoay vòng Google API Key (chuyển sang key index %d/%d)",
                    self._key_index + 1,
                    len(self._keys),
                )
                return next_key
            return self._keys[self._key_index % len(self._keys)]

    def _call_api_with_retry(self, method: str, endpoint: str, json_body: dict) -> dict:
        """Gửi request tới Google API với retry và xoay vòng key khi gặp 429/quota."""
        max_attempts = max(len(self._keys) * 2, 3)

        for attempt in range(max_attempts):
            api_key = self._get_current_key()
            url = f"{GOOGLE_API_BASE_URL}/{self._model}:{endpoint}?key={api_key}"

            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.request(method, url, json=json_body)

                if response.status_code == 200:
                    return response.json()

                if response.status_code in (429, 503) or "RESOURCE_EXHAUSTED" in response.text:
                    logger.warning(
                        "Google API trả về mã lỗi %d (hết quota/rate limit). Thử xoay key... (Lần %d/%d)",
                        response.status_code,
                        attempt + 1,
                        max_attempts,
                    )
                    self._rotate_key(api_key)
                    time.sleep(1.0)
                    continue

                if response.status_code in (401, 403):
                    raise EmbeddingAuthError(
                        f"Google API Key không hợp lệ hoặc không có quyền gọi {self._model}: {response.text}"
                    )

                raise EmbeddingServerError(
                    f"Google Embedding API trả về mã lỗi {response.status_code}: {response.text}"
                )

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                logger.warning("Lỗi mạng khi gọi Google Embedding API: %s. Thử lại...", net_err)
                if attempt == max_attempts - 1:
                    raise EmbeddingServiceError(f"Không thể kết nối tới Google API: {net_err}") from net_err
                time.sleep(1.0)

        raise EmbeddingServiceError("Tất cả Google API Keys đều bị vượt hạn mức quota hoặc lỗi.")

    def embed_query(self, text: str) -> List[float]:
        """Nhúng một câu hỏi truy vấn (dùng khi tìm kiếm RAG)."""
        if not text or not text.strip():
            return [0.0] * self._dimension

        collector = current_timing()
        start_time = time.perf_counter_ns()

        payload = {
            "model": self._model,
            "content": {"parts": [{"text": text.strip()}]},
            "taskType": "RETRIEVAL_QUERY",
            "outputDimensionality": self._dimension,
        }

        data = self._call_api_with_retry("POST", "embedContent", payload)
        embedding_obj = data.get("embedding", {})
        values = embedding_obj.get("values", [])

        if len(values) != self._dimension:
            raise EmbeddingServiceError(
                f"Độ dài vector nhận được ({len(values)}) không khớp kích thước yêu cầu ({self._dimension})"
            )

        if collector is not None:
            collector.add_duration("query_embedding", (time.perf_counter_ns() - start_time) / 1_000_000)

        return values

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Nhúng danh sách tài liệu theo từng lô (dùng khi indexing)."""
        if not texts:
            return []

        all_vectors: List[List[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            requests = [
                {
                    "model": self._model,
                    "content": {"parts": [{"text": t if t and t.strip() else " "}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "outputDimensionality": self._dimension,
                }
                for t in batch
            ]

            payload = {"requests": requests}
            data = self._call_api_with_retry("POST", "batchEmbedContents", payload)
            embeddings = data.get("embeddings", [])

            if len(embeddings) != len(batch):
                raise EmbeddingServiceError(
                    f"Số lượng vector trả về ({len(embeddings)}) không khớp số văn bản trong batch ({len(batch)})"
                )

            for item in embeddings:
                vals = item.get("values", [])
                if len(vals) != self._dimension:
                    raise EmbeddingServiceError(
                        f"Kích thước vector ({len(vals)}) không khớp chuẩn ({self._dimension})"
                    )
                all_vectors.append(vals)

        return all_vectors
