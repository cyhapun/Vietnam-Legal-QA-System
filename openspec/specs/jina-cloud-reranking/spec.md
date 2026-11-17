# Jina Cloud Reranking

## Purpose

Provide true multilingual cross-encoder reranking in `cloud` mode via the Jina AI Reranker REST API (`https://api.jina.ai/v1/rerank`), requiring zero local ML packages and supporting multi-key rotation and fail-open resilience.

## Requirements

### Requirement: Jina AI Cross-Encoder Reranker adapter

The backend MUST implement `JinaReranker` conforming to `BaseReranker` using `httpx` against Jina AI's `/v1/rerank` endpoint with `jina-reranker-v2-base-multilingual` as the default model.

#### Scenario: Successful reranking preserves Document objects and metadata

- **WHEN** `JinaReranker.rerank(query, documents, top_k)` is called with a non-empty list of candidate `Document` instances
- **THEN** it sends `POST https://api.jina.ai/v1/rerank` with `Authorization: Bearer <key>`, `model`, `query`, `documents` (truncated to `max_candidates`), `top_n=min(top_k, len(candidates))`, and `return_documents=false`
- **AND** it maps each returned `results[].index` back to the original `Document` object (preserving full `page_content` and legal `metadata`) in descending `relevance_score` order
- **AND** it records reranking latency in `current_timing()` when pipeline timing is active

#### Scenario: Empty or single-document short-circuit

- **WHEN** `documents` is empty or `top_k <= 0`
- **THEN** `JinaReranker.rerank` returns `[]` immediately without making an HTTP request

### Requirement: Multi-key rotation and fail-open resilience

`JinaReranker` MUST support comma-separated `JINA_API_KEY` rotation on rate-limit responses and fail open to the original retrieval order when configured.

#### Scenario: Rate-limit rotation across keys

- **WHEN** Jina AI returns HTTP `429` or `503` and multiple keys are configured in `JINA_API_KEY`
- **THEN** `JinaReranker` rotates to the next key and retries the request

#### Scenario: Fail-open fallback on API or network error

- **WHEN** all retry attempts fail (e.g., timeout, network error, exhausted quota, or auth error) and `fail_open=True`
- **THEN** `JinaReranker` logs a warning without exposing the API key and returns `documents[:top_k]` in their original retrieval order so chat generation continues uninterrupted

#### Scenario: Strict failure when fail-open is disabled

- **WHEN** all retry attempts fail and `fail_open=False`
- **THEN** `JinaReranker` raises an explicit error describing the HTTP status or network failure without leaking credentials
