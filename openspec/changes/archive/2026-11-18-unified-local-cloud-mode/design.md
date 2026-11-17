# Design: Unified Local & Cloud Runtime Mode with Jina Reranker

## Context

The Vietnam Legal QA System currently runs on Supabase PostgreSQL + Qdrant Cloud for data storage, Google AI Studio Gemini for LLM generation, and fine-tuned local BGE-M3 / BGE-Reranker-v2-M3 weights for local retrieval and reranking. Previously, `serverless` mode relied on Hugging Face Serverless Inference API (`BAAI/bge-m3` + bi-encoder `embedding_similarity`), which is now blocked on free HF accounts by `402 Payment Required`.

The goal is a clean, minimal 1-line switch in `.env` (`RUNTIME_PROFILE=local` vs `RUNTIME_PROFILE=cloud`) that cleanly coordinates Embedding, Reranking, Qdrant collection, Semantic Cache collection, model preloading, and readiness diagnostics without risking the existing 5,758 BGE-M3 vectors.

## Goals / Non-Goals

**Goals:**
- Single minimal toggle `RUNTIME_PROFILE=local|cloud` in `.env` (accepting `serverless` as an alias for `cloud` for Vercel compatibility).
- Full `cloud` stack using **Google Gemini Embedding (`models/gemini-embedding-001`, 1024d)** + **Jina AI Cross-Encoder Reranker (`jina-reranker-v2-base-multilingual`)** + **Google Gemini LLM**, with zero Hugging Face dependency and zero local ML weights.
- Automatic parallel Qdrant & semantic cache collection isolation (`vietlaw_clauses` / `semantic_cache` for `local`; `vietlaw_clauses_gemini` / `semantic_cache_gemini` for `cloud`).
- Safe, clone-and-resume Gemini re-indexing script so `vietlaw_clauses` is never overwritten and quota-limited runs can resume across keys or days.
- Synchronous updates across `config.py`, `pipeline.py`, `main.py`, `vercel.json`, `docker-compose.yml`, `.env`, `.env.example`, and unit tests.

**Non-Goals:**
- Runtime UI toggle for switching between `local` and `cloud` per chat request (env-driven startup switch only).
- Removing existing `HuggingFaceEndpointEmbedding` or `HuggingFaceEmbeddingSimilarityReranker` classes (keep them intact for local mode and backward compatibility).
- Changing Qdrant dense vector dimensionality (remains 1024-dim Cosine in both collections).

## Decisions

### 1. Normalize `RUNTIME_PROFILE` to `local` | `cloud` (with `serverless` alias)

In `backend/app/config.py`:
- Raw env value `_raw_profile = os.getenv("RUNTIME_PROFILE", "").strip().lower()` (defaults to `"cloud"` when `VERCEL` or `VERCEL_ENV` is set, otherwise `"local"`).
- Normalize `"serverless"` → `"cloud"` so existing `VERCEL` / `vercel.json` / legacy tests continue working seamlessly.
- `SUPPORTED_RUNTIME_PROFILES = frozenset({"local", "cloud"})` (validation rejects any other raw value such as `"invalid"`).

Automatic defaults derived from `RUNTIME_PROFILE` (each still overridable via explicit env var):

| Config | `RUNTIME_PROFILE=local` | `RUNTIME_PROFILE=cloud` |
| :--- | :--- | :--- |
| `EMBEDDING_PROVIDER` | `huggingface` | `gemini` |
| `HUGGINGFACE_EMBEDDING_MODE` | `local` | `api` *(unused when provider=gemini)* |
| `EMBEDDING_MODEL` | `../models/embedding/vietlaw-bge-m3-finetuned/best` | `models/gemini-embedding-001` |
| `PIPELINE_RERANKING` | `cross_encoder` | `jina` |
| `RERANKER_MODEL` | `../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected` | `jina-reranker-v2-base-multilingual` |
| `QDRANT_COLLECTION` | `vietlaw_clauses` | `vietlaw_clauses_gemini` |
| `SEMANTIC_CACHE_COLLECTION` | `semantic_cache` | `semantic_cache_gemini` |
| `LOCAL_MODELS_PRELOAD_ENABLED` | `true` | `false` |
| `LOCAL_MODELS_WARMUP_ENABLED` | `true` | `false` |

### 2. `JinaReranker` Adapter Architecture

Create `backend/app/services/reranking/jina_reranker.py` conforming to `BaseReranker`:
- **Endpoint**: `POST https://api.jina.ai/v1/rerank` (configurable via `JINA_RERANKER_URL`).
- **Auth**: `Authorization: Bearer <key>`, parsed from `JINA_API_KEY` (supports comma-separated keys for round-robin rotation on HTTP `429`/`503`, matching `GeminiEmbedding`).
- **Payload**:
  ```json
  {
    "model": "jina-reranker-v2-base-multilingual",
    "query": "<query>",
    "documents": ["<doc_0>", "<doc_1>", "..."],
    "top_n": 5,
    "return_documents": false
  }
  ```
- **Index mapping**: Map `results[].index` back to the candidate `Document` slice (`candidate_docs[idx]`) while preserving full legal metadata (`law_id`, `article`, `clause`, `category`, etc.) and recording `relevance_score` cleanly if helpful, without mutating original content.
- **Timing**: Record reranking duration via `current_timing().mark_reranking(...)` (check exact method name on `PipelineTimingCollector` during implementation so metrics stay consistent with `CrossEncoderReranker`).
- **Resilience**: Default `fail_open=True` in cloud mode (configurable via `JINA_RERANKER_FAIL_OPEN` / constructor) so transient network/quota errors degrade gracefully to retrieval order `documents[:top_k]` rather than breaking user answers.

### 3. Pipeline Wiring & Readiness Diagnostics

- `backend/app/services/pipeline.py`:
  - `_create_reranker()` handles `strategy == "jina"` → `JinaReranker(model=JINA_RERANKER_MODEL, max_candidates=max_candidates, fail_open=...)`.
  - If `RUNTIME_PROFILE == "cloud"` and `strategy == "cross_encoder"`, log warning and fall back to `"jina"` (instead of legacy `"embedding_similarity"`).
  - `_get_embedding()` already routes `EMBEDDING_PROVIDER == "gemini"` → `GeminiEmbedding()`. Ensure cache key includes `EMBEDDING_PROVIDER` as well as `RUNTIME_PROFILE`.
- `backend/app/main.py`:
  - `_check_artifacts()` cleanly reports `embedding` (`provider`, `mode`, `model`, `weights`) and `reranker` (`provider`, `mode`, `model`, `enabled`, `weights`) for both `local` and `cloud` profiles.
  - Validates `GOOGLE_API_KEYS` and `JINA_API_KEY` presence in `cloud` mode via `validate_runtime_configuration()`.

### 4. Clone & Resumable `reindex_gemini_cloud.py`

Update `backend/scripts/reindex_gemini_cloud.py`:
- Source collection: `--source` (default `vietlaw_clauses`) — **read-only**.
- Target collection: `--target` (default `vietlaw_clauses_gemini`).
- Ensure target collection exists with identical schema:
  - `vectors_config={"text-dense": VectorParams(size=1024, distance=Distance.COSINE)}`
  - `sparse_vectors_config={"text-sparse": SparseVectorParams(modifier=Modifier.IDF)}`
  - Payload indexes: `category` (`KEYWORD`) and `law_id` (`KEYWORD`).
- Before embedding each scrolled batch from source, query target collection with `client.retrieve(target, ids=batch_ids, with_vectors=False, with_payload=False)` to filter out IDs that already exist in `vietlaw_clauses_gemini`.
- Only embed & upsert missing points; print clear progress + remaining count if stopped by daily quota (`429`).

### 5. Deployment Config Cleanup

- `vercel.json`: Replace `RUNTIME_PROFILE: "serverless"` and all `HUGGINGFACE_*` / `PIPELINE_RERANKING` overrides with `"RUNTIME_PROFILE": "cloud"`, `"CHAT_STORAGE_MODE": "browser"`, `"NEXT_PUBLIC_CHAT_STORAGE_MODE": "browser"`.
- `docker-compose.yml`: Avoid hardcoding `HUGGINGFACE_EMBEDDING_MODE`, `HUGGINGFACE_EMBEDDING_MODEL`, `EMBEDDING_PROVIDER`, `QDRANT_COLLECTION`, or `SEMANTIC_CACHE_COLLECTION` to local-only defaults that would override `RUNTIME_PROFILE=cloud` from `.env` (pass through or let `config.py` derive them cleanly).
- `.env` & `.env.example`: Minimal 5-section layout with `RUNTIME_PROFILE=local` at the top and `JINA_API_KEY` alongside `GOOGLE_API_KEYS`.

## Risks / Trade-offs

- **Google Free Tier 1,000 RPD for initial Gemini indexing**: `vietlaw_clauses_gemini` requires 5,758 embeddings once. Mitigated by keeping `vietlaw_clauses` intact and making `reindex_gemini_cloud.py` resumable + multi-key.
- **Jina Free Tier 10M token pool**: Shared across all Jina endpoints; reranking 10 legal clauses per query consumes ~2–3k tokens (~3,000–5,000 queries free per key). Mitigated by supporting comma-separated `JINA_API_KEY` rotation and `fail_open=True`.
- **Legacy tests referencing `serverless` or `embedding_similarity`**: Mitigated by aliasing `serverless` → `cloud` and keeping `embedding_similarity` supported when explicitly configured via `PIPELINE_RERANKING=embedding_similarity`.
