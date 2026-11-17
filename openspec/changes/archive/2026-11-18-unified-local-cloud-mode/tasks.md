# Implementation Tasks: Unified Local & Cloud Runtime Mode with Jina Reranker

## 1. Configuration & Runtime Profile Unification
- [x] 1.1 Update `backend/app/config.py` to normalize `RUNTIME_PROFILE` (`local` | `cloud`, aliasing `serverless` → `cloud`) and derive defaults for `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `PIPELINE_RERANKING`, `RERANKER_MODEL`, `QDRANT_COLLECTION`, `SEMANTIC_CACHE_COLLECTION`, and local preload/warmup flags.
- [x] 1.2 Add Jina configuration variables in `backend/app/config.py` (`JINA_API_KEY`, `JINA_RERANKER_MODEL`, `JINA_RERANKER_URL`, `JINA_RERANKER_TIMEOUT`, `JINA_RERANKER_FAIL_OPEN`).
- [x] 1.3 Update `validate_runtime_configuration()` and `runtime_profile_summary()` in `backend/app/config.py` for `local` and `cloud` validation rules without exposing secrets.

## 2. Jina Cloud Reranker Implementation
- [x] 2.1 Inspect `PipelineTimingCollector` in `backend/app/services/pipeline_timing.py` to match existing reranking timing instrumentation.
- [x] 2.2 Implement `JinaReranker` in `backend/app/services/reranking/jina_reranker.py` conforming to `BaseReranker` (`POST https://api.jina.ai/v1/rerank`, `return_documents=false`, index-to-Document mapping, multi-key rotation on `429`/`503`, timing metrics, and `fail_open` fallback).
- [x] 2.3 Export `JinaReranker` in `backend/app/services/reranking/__init__.py`.

## 3. Pipeline & Readiness Diagnostics Integration
- [x] 3.1 Wire `strategy == "jina"` in `backend/app/services/pipeline.py` (`_create_reranker()`) and update cloud fallback from `cross_encoder` → `jina`.
- [x] 3.2 Update `_get_embedding()` cache key in `backend/app/services/pipeline.py` to include `EMBEDDING_PROVIDER`.
- [x] 3.3 Update `_check_artifacts()` in `backend/app/main.py` so `/readiness` accurately reports `gemini` embedding and `jina` reranker diagnostics in `cloud` mode.

## 4. Safe Clone & Resumable Gemini Re-indexing Script
- [x] 4.1 Refactor `backend/scripts/reindex_gemini_cloud.py` to clone read-only from `vietlaw_clauses` into `vietlaw_clauses_gemini` (preserving `payload`, `text-sparse`, and creating `category`/`law_id` keyword payload indexes).
- [x] 4.2 Add resume detection (skip IDs already present in target collection) and CLI flags (`--source`, `--target`, `--batch-size`, `--dry-run`).

## 5. Environment Templates & Deployment Sync
- [x] 5.1 Streamline `.env` (including user's `JINA_API_KEY`, gitignored) and `.env.example` (clean placeholders) to the minimal 1-line `RUNTIME_PROFILE=local|cloud` structure.
- [x] 5.2 Update `vercel.json` to use `"RUNTIME_PROFILE": "cloud"` and remove obsolete `HUGGINGFACE_*` / `embedding_similarity` env entries.
- [x] 5.3 Update `docker-compose.yml` so local-only defaults do not override `RUNTIME_PROFILE=cloud` from `.env`.

## 6. Verification & Testing
- [x] 6.1 Add unit tests in `backend/tests/test_runtime_modes_and_jina.py` covering `local` & `cloud`/`serverless` config resolution, validation errors, `JinaReranker` (ranking order, metadata preservation, key rotation, `fail_open`), and `/readiness` in `cloud` mode.
- [x] 6.2 Run full backend test suite (`pytest tests/`) and verify live connectivity of `JinaReranker` with the provided `JINA_API_KEY`.
- [x] 6.3 Verify local server startup and `/readiness` under `RUNTIME_PROFILE=local` (confirming zero regressions on existing `vietlaw_clauses` setup).
