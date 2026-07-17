"""Remote Hugging Face reranker for deployment environments."""
from __future__ import annotations

import json
import math
from typing import List
from urllib import error, request

from langchain_core.documents import Document

from app.config import HUGGINGFACE_API_KEY, PIPELINE_CONFIG
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.reranking.hf_inference")


class HuggingFaceInferenceReranker:
    """Call a Hugging Face hosted BGE reranker and keep local reranker semantics."""

    def __init__(
        self,
        model: str | None = None,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        batch_size: int | None = None,
        max_length: int | None = None,
        fail_open: bool | None = None,
        timeout: float = 60.0,
    ):
        self._model = model or PIPELINE_CONFIG.get("reranker_api_model", "BAAI/bge-reranker-v2-m3")
        self._endpoint_url = endpoint_url or PIPELINE_CONFIG.get(
            "reranker_api_url",
            "https://api-inference.huggingface.co/models/BAAI/bge-reranker-v2-m3",
        )
        self._api_key = api_key or HUGGINGFACE_API_KEY
        self._batch_size = batch_size if batch_size is not None else PIPELINE_CONFIG.get("reranker_batch_size", 8)
        self._max_length = max_length if max_length is not None else PIPELINE_CONFIG.get("reranker_max_length", 512)
        self._fail_open = PIPELINE_CONFIG.get("reranker_fail_open", False) if fail_open is None else fail_open
        self._timeout = timeout

        if self._batch_size <= 0:
            raise ValueError(f"RERANKER_BATCH_SIZE must be greater than 0; got {self._batch_size}.")
        if self._max_length <= 0:
            raise ValueError(f"RERANKER_MAX_LENGTH must be greater than 0; got {self._max_length}.")
        if not self._api_key:
            raise ValueError("HUGGINGFACE_API_KEY is required when RERANKER_MODE=api.")

        logger.info(
            "Remote HuggingFace reranker configured: model=%s endpoint=%s batch_size=%d max_length=%d fail_open=%s",
            self._model,
            self._endpoint_url,
            self._batch_size,
            self._max_length,
            self._fail_open,
        )

    @property
    def strategy_name(self) -> str:
        return f"hf_inference_reranker({self._model})"

    def _call(self, query: str, text: str, api_key: Optional[str] = None) -> float:
        payload = json.dumps(
            {
                "inputs": {
                    "source_sentence": query,
                    "sentences": [text],
                },
                "parameters": {
                    "truncate": True,
                    "max_length": self._max_length,
                },
            }
        ).encode("utf-8")
        req = request.Request(
            self._endpoint_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key or self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Hugging Face reranker request failed: HTTP {exc.code} {detail}") from exc

        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, dict):
                value = first.get("score", first.get("label", first.get("logit")))
            else:
                value = first
        elif isinstance(body, dict):
            value = body.get("score", body.get("logit"))
        else:
            value = None

        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Unexpected Hugging Face reranker response: {body}") from exc
        if not math.isfinite(score):
            raise RuntimeError("Remote reranker returned NaN or Inf.")
        return score

    def _score(self, query: str, documents: List[Document], api_key: Optional[str] = None) -> List[float]:
        return [self._call(query, doc.page_content, api_key=api_key) for doc in documents]

    @staticmethod
    def _fail_open_result(documents: List[Document], top_k: int) -> List[Document]:
        return documents[:max(0, top_k)]

    def rerank(self, query: str, documents: List[Document], top_k: int, api_key: Optional[str] = None) -> List[Document]:
        if not documents or top_k <= 0:
            return []

        try:
            scores = self._score(query, documents, api_key=api_key)
        except Exception as exc:
            if self._fail_open:
                logger.warning("Remote reranker failed open; preserving original order: %s", exc)
                return self._fail_open_result(documents, top_k)
            raise RuntimeError(f"Remote Hugging Face reranking failed for {self._model}: {exc}") from exc

        scored_docs = []
        for index, (score, doc) in enumerate(zip(scores, documents)):
            metadata = dict(doc.metadata or {})
            metadata["rerank_score"] = score
            scored_docs.append((score, index, Document(page_content=doc.page_content, metadata=metadata)))
        scored_docs.sort(key=lambda item: (-item[0], item[1]))
        return [doc for _, _, doc in scored_docs[:top_k]]
