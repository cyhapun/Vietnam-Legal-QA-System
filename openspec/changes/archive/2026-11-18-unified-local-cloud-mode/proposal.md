# Proposal: Unified Local & Cloud Runtime Mode with Jina Reranker

## Why

Currently, switching between local fine-tuned models and cloud API models requires editing 4–6 tightly coupled environment variables (`RUNTIME_PROFILE`, `EMBEDDING_PROVIDER`, `HUGGINGFACE_EMBEDDING_MODE`, `HUGGINGFACE_EMBEDDING_MODEL`, `PIPELINE_RERANKING`, `RERANKER_MODEL`, `QDRANT_COLLECTION`). In addition:

1. **Hugging Face Inference API is no longer viable on the free tier**: `router.huggingface.co` returns `402 Payment Required` for both embedding (`BAAI/bge-m3`) and reranking (`BAAI/bge-reranker-v2-m3`) on accounts without prepaid credits or PRO.
2. **Cloud reranking lacks a true Cross-Encoder**: The existing `embedding_similarity` fallback computes bi-encoder cosine similarity via embedding API calls rather than true cross-encoder reranking.
3. **Vector space safety between local and cloud**: Local fine-tuned `vietlaw-bge-m3-finetuned` (BGE-M3 1024d) and cloud `models/gemini-embedding-001` (Gemini 1024d) occupy incompatible vector spaces. Running both modes against a single Qdrant collection would corrupt retrieval or destroy local vectors during re-indexing.

By unifying the mode toggle into a single minimal variable (`RUNTIME_PROFILE=local|cloud`, keeping `serverless` as a backward-compatible alias for `cloud`), pairing **Gemini Embedding + Jina Multilingual Cross-Encoder Reranker** for `cloud` mode, and automatically isolating Qdrant & semantic cache collections per profile, developers and deployments can switch cleanly between full-local and full-cloud with one line in `.env`.

## What Changes

- **Minimal 1-line mode switch in `.env` & `.env.example`**:
  - `RUNTIME_PROFILE=local` automatically selects local fine-tuned BGE-M3 embedding, local fine-tuned BGE-Reranker-v2-M3 cross-encoder, `vietlaw_clauses`, `semantic_cache`, and model preloading.
  - `RUNTIME_PROFILE=cloud` (alias `serverless`) automatically selects Google Gemini Embedding (`models/gemini-embedding-001`, 1024d), Jina AI Cross-Encoder Reranker (`jina-reranker-v2-base-multilingual`), `vietlaw_clauses_gemini`, `semantic_cache_gemini`, and zero local ML preloading.
  - Explicit env overrides remain supported when needed, without cluttering the minimal `.env`.
- **New Jina Cloud Reranker (`JinaReranker`)**:
  - Implement `backend/app/services/reranking/jina_reranker.py` conforming to `BaseReranker` using `httpx` against `https://api.jina.ai/v1/rerank`.
  - Use `return_documents: false` to minimize bandwidth while preserving original `Document` objects and legal metadata by index.
  - Support comma-separated `JINA_API_KEY` key rotation on `429`, pipeline timing metrics, and `fail_open=True` fallback to retrieval order on transient errors.
- **Parallel Qdrant collection isolation & resumable Gemini clone script**:
  - Automatically default Qdrant & semantic cache collections by profile (`vietlaw_clauses` / `semantic_cache` for `local`; `vietlaw_clauses_gemini` / `semantic_cache_gemini` for `cloud`).
  - Upgrade `backend/scripts/reindex_gemini_cloud.py` from in-place overwrite to a safe **clone & resumable** workflow: read from `vietlaw_clauses`, preserve `payload`, `text-sparse`, and payload indexes (`category`, `law_id`), skip already-indexed IDs in `vietlaw_clauses_gemini`, and support multi-key Gemini rotation.
- **Deployment & diagnostics sync**:
  - Update `backend/app/main.py` `/readiness` artifact diagnostics for `cloud` (`gemini` embedding + `jina` reranker).
  - Update `vercel.json` and `docker-compose.yml` so legacy `HUGGINGFACE_*` defaults do not override `RUNTIME_PROFILE=cloud`.
  - Add unit tests covering profile defaults, validation, `JinaReranker`, and cloud readiness.

## Capabilities

### New Capabilities
- `jina-cloud-reranking`: True cross-encoder cloud reranking via Jina AI `/v1/rerank` (`jina-reranker-v2-base-multilingual`) with multi-key rotation, timing instrumentation, and `fail_open` safety.

### Modified Capabilities
- `deployment-runtime-profiles`: Evolve runtime profiles from `local` / `serverless` (HF API) to unified `local` / `cloud` (with `serverless` alias) using Gemini Embedding + Jina Reranker in `cloud` mode and automatic parallel Qdrant & semantic cache collection isolation.

## Impact

- **Backend**: `backend/app/config.py`, `backend/app/main.py`, `backend/app/services/pipeline.py`, `backend/app/services/reranking/__init__.py`, `backend/app/services/reranking/jina_reranker.py` (new), `backend/scripts/reindex_gemini_cloud.py`, `backend/tests/`.
- **Config & Deployment**: `.env`, `.env.example`, `vercel.json`, `docker-compose.yml`.
- **Dependencies**: Zero new Python packages required (`httpx` is already installed in `backend/requirements.txt`).
- **Existing Data**: Zero risk to the existing 5,758 BGE-M3 vectors in `vietlaw_clauses` (preserved untouched for `local` mode).
