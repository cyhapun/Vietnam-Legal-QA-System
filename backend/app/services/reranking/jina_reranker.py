"""Jina AI cloud cross-encoder reranker adapter."""
from __future__ import annotations

import threading
import time
from typing import List, Optional

import httpx
from langchain_core.documents import Document

from app.config import (
    JINA_API_KEY,
    JINA_RERANKER_FAIL_OPEN,
    JINA_RERANKER_MODEL,
    JINA_RERANKER_TIMEOUT,
    JINA_RERANKER_URL,
)
from app.services.pipeline_timing import current_timing
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.reranking.jina")


def _parse_keys(raw_keys: Optional[List[str] | str]) -> List[str]:
    """Parse one or more comma-separated Jina API keys."""
    if isinstance(raw_keys, list):
        keys = [k.strip() for k in raw_keys if k and k.strip()]
        if keys:
            return keys

    raw = raw_keys if isinstance(raw_keys, str) and raw_keys.strip() else JINA_API_KEY
    keys: List[str] = []
    for part in str(raw or "").split(","):
        cleaned = part.strip()
        if cleaned and cleaned not in keys:
            keys.append(cleaned)
    return keys


class JinaReranker:
    """Cloud multilingual cross-encoder reranker powered by Jina AI /v1/rerank."""

    def __init__(
        self,
        model: str = JINA_RERANKER_MODEL,
        api_key: Optional[str | List[str]] = None,
        api_url: str = JINA_RERANKER_URL,
        max_candidates: int = 10,
        timeout: float = JINA_RERANKER_TIMEOUT,
        fail_open: Optional[bool] = None,
    ):
        self._model = (model or JINA_RERANKER_MODEL).strip()
        self._api_url = (api_url or JINA_RERANKER_URL).strip()
        self._max_candidates = max(1, int(max_candidates))
        self._timeout = float(timeout)
        self._fail_open = JINA_RERANKER_FAIL_OPEN if fail_open is None else bool(fail_open)
        self._keys = _parse_keys(api_key)
        self._key_index = 0
        self._lock = threading.Lock()

        logger.info(
            "JinaReranker configured: model=%s max_candidates=%d keys_count=%d fail_open=%s",
            self._model,
            self._max_candidates,
            len(self._keys),
            self._fail_open,
        )

    @property
    def strategy_name(self) -> str:
        return f"jina({self._model})"

    def _resolve_keys(self, override_api_key: Optional[str] = None) -> List[str]:
        if override_api_key and override_api_key.strip():
            return _parse_keys(override_api_key)
        return self._keys

    def _get_current_key(self, keys: List[str]) -> str:
        with self._lock:
            return keys[self._key_index % len(keys)]

    def _rotate_key(self, keys: List[str], failed_key: str) -> None:
        if len(keys) <= 1:
            return
        with self._lock:
            if keys[self._key_index % len(keys)] == failed_key:
                self._key_index = (self._key_index + 1) % len(keys)
                logger.warning(
                    "Rotated Jina API key to index %d/%d after transient status.",
                    self._key_index + 1,
                    len(keys),
                )

    def _call_rerank_api(
        self,
        query: str,
        texts: List[str],
        top_n: int,
        keys: List[str],
    ) -> dict:
        if not keys:
            raise RuntimeError("JINA_API_KEY is missing or empty.")

        payload = {
            "model": self._model,
            "query": query,
            "documents": [text if text and text.strip() else " " for text in texts],
            "top_n": top_n,
            "return_documents": False,
        }
        max_attempts = max(len(keys) * 2, 2)
        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            active_key = self._get_current_key(keys)
            headers = {
                "Authorization": f"Bearer {active_key}",
                "Content-Type": "application/json",
            }
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(self._api_url, headers=headers, json=payload)

                if response.status_code == 200:
                    return response.json()

                if response.status_code in (429, 503):
                    last_error = RuntimeError(
                        f"Jina Rerank API transient HTTP {response.status_code}"
                    )
                    logger.warning(
                        "Jina Rerank API returned HTTP %d (attempt %d/%d).",
                        response.status_code,
                        attempt + 1,
                        max_attempts,
                    )
                    self._rotate_key(keys, active_key)
                    if attempt < max_attempts - 1:
                        time.sleep(0.5)
                    continue

                if response.status_code in (401, 402, 403):
                    raise RuntimeError(
                        f"Jina Rerank API auth/billing error HTTP {response.status_code}."
                    )

                raise RuntimeError(
                    f"Jina Rerank API returned HTTP {response.status_code}: {response.text[:300]}"
                )
            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                last_error = RuntimeError(f"Jina Rerank API network error: {net_err}")
                logger.warning(
                    "Jina Rerank API network/timeout error (attempt %d/%d): %s",
                    attempt + 1,
                    max_attempts,
                    net_err,
                )
                if attempt < max_attempts - 1:
                    time.sleep(0.5)
                    continue

        raise last_error or RuntimeError("Jina Rerank API failed after all retry attempts.")

    @staticmethod
    def _fail_open_result(documents: List[Document], top_k: int) -> List[Document]:
        return documents[: max(0, top_k)]

    def _map_results(
        self,
        data: dict,
        candidate_docs: List[Document],
        top_k: int,
    ) -> List[Document]:
        raw_results = data.get("results")
        if not isinstance(raw_results, list) or not raw_results:
            raise RuntimeError("Jina Rerank API returned empty or malformed 'results'.")

        indexed_items = []
        seen_indices = set()
        for position, item in enumerate(raw_results):
            if not isinstance(item, dict):
                continue
            idx = item.get("index")
            if not isinstance(idx, int) or idx < 0 or idx >= len(candidate_docs):
                continue
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            score = float(item.get("relevance_score", 0.0))
            indexed_items.append((score, position, idx))

        if not indexed_items:
            raise RuntimeError("Jina Rerank API returned no valid candidate indices.")

        indexed_items.sort(key=lambda entry: (-entry[0], entry[1]))
        ranked_docs: List[Document] = []
        for score, _, idx in indexed_items[:top_k]:
            original = candidate_docs[idx]
            metadata = dict(original.metadata or {})
            metadata["rerank_score"] = score
            ranked_docs.append(Document(page_content=original.page_content, metadata=metadata))
        return ranked_docs

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        if not documents or top_k <= 0:
            return []

        candidate_docs = documents[: max(top_k, self._max_candidates)]
        top_n = min(top_k, len(candidate_docs))
        keys = self._resolve_keys(api_key)

        collector = current_timing()
        try:
            if collector is not None:
                with collector.stage("reranking"):
                    data = self._call_rerank_api(
                        query=query,
                        texts=[doc.page_content for doc in candidate_docs],
                        top_n=top_n,
                        keys=keys,
                    )
                    results = self._map_results(data, candidate_docs, top_k)
            else:
                data = self._call_rerank_api(
                    query=query,
                    texts=[doc.page_content for doc in candidate_docs],
                    top_n=top_n,
                    keys=keys,
                )
                results = self._map_results(data, candidate_docs, top_k)
        except Exception as exc:
            if self._fail_open:
                logger.warning(
                    "JinaReranker failed open; preserving retrieval order: %s",
                    exc,
                )
                return self._fail_open_result(documents, top_k)
            raise RuntimeError(f"JinaReranker failed for {self._model}: {exc}") from exc

        top_score = results[0].metadata.get("rerank_score", 0.0) if results else 0.0
        logger.info(
            "JinaReranker (%s) reranked %d -> %d documents (top score: %.4f)",
            self._model,
            len(candidate_docs),
            len(results),
            top_score,
        )
        return results
