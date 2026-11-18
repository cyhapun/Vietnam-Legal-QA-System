# Local Model Integration

When `RUNTIME_PROFILE=local` is active, the backend loads fine-tuned retrieval and reranking weights directly from the local filesystem with zero cloud embedding or reranking API calls:

```text
local backend (RUNTIME_PROFILE=local)
-> fine-tuned BGE-M3 query embedding (local filesystem)
-> Qdrant hybrid retrieval (vietlaw_clauses)
-> fine-tuned BGE-Reranker-v2-M3 cross-encoder (local filesystem)
-> 2-level nested context builder
-> Google AI Studio LLM (gemini-3.1-flash-lite + fallbacks)
```

> Local mode refers to local model inference; PostgreSQL and Qdrant may run either locally via Docker or on cloud services (Supabase + Qdrant Cloud).

## Artifacts & Validated Hashes

Expected paths relative to the repository root (also mounted read-only at `/models` inside Docker containers; `models/` is gitignored):

- Embedding: `models/embedding/vietlaw-bge-m3-finetuned/best`
- Reranker candidate `002-001`: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-002-001`
- Reranker candidate `003-004`: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-003-004`
- Active reranker symlink: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected`

Validated `model.safetensors` SHA-256 hashes:

- Embedding: `a318ac316747eab2d429692a84d17ff25f038cb3b182f159ee97e313034a0e02`
- Reranker `candidate-002-001`: `6d15b6914846cd6ac1006badd256e325c93e80de975a26b46d647d7a51c0432e`
- Reranker `candidate-003-004`: `bdeb8e6771c7e97dd64136317c645529f10e4060c8e0578832f3dd1b6caa7079`

`selected` currently points to `candidate-003-004` as a provisional operational choice; `candidate-002-001` remains available for symlink rollback.

## Configuration

Minimal `.env` for local mode (defaults are derived automatically from `RUNTIME_PROFILE=local`):

```env
RUNTIME_PROFILE=local
GOOGLE_API_KEYS=your_google_api_key
POSTGRES_DSN=postgresql://postgres:postgres@localhost:15432/vietlaw
QDRANT_URL=https://<your-qdrant-host>:6333
QDRANT_API_KEY=<your-qdrant-api-key>
```

Derived local defaults (override only if needed):

- `EMBEDDING_PROVIDER=huggingface`, `HUGGINGFACE_EMBEDDING_MODE=local`
- `HUGGINGFACE_EMBEDDING_MODEL=../models/embedding/vietlaw-bge-m3-finetuned/best`
- `PIPELINE_RERANKING=cross_encoder`, `RERANKER_MODEL=../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected`
- `QDRANT_COLLECTION=vietlaw_clauses`, `SEMANTIC_CACHE_COLLECTION=semantic_cache`
- `LOCAL_MODELS_PRELOAD_ENABLED=true`, `LOCAL_MODELS_WARMUP_ENABLED=true`, `LOCAL_MODELS_OFFLINE=true`

## Offline Enforcement & Safety

- When `LOCAL_MODELS_OFFLINE=true`, the backend sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` and loads models with `local_files_only=True`.
- Missing or invalid local artifacts fail fast during startup/readiness instead of silently calling remote APIs or querying a mismatched vector space.
- `ENABLE_FAISS_FALLBACK` is disabled (`False`) to prevent falling back to a stale FAISS index.
- Never query `vietlaw_clauses` (BGE-M3 vectors) with a different embedding model. Cloud mode uses its own isolated collection (`vietlaw_clauses_gemini`) and cache (`semantic_cache_gemini`).

## Validation

Validate local artifacts offline from `backend/`:

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python scripts/validate_local_models.py \
  --embedding-path ../models/embedding/vietlaw-bge-m3-finetuned/best \
  --skip-reranker

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python scripts/validate_local_models.py \
  --skip-embedding \
  --reranker-path ../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
```

Smoke-test retrieval without LLM generation:

```bash
cd backend
ENABLE_SEMANTIC_CACHE=false PYTHONPATH=. .venv/bin/python - <<'PY'
from app.services.pipeline import get_pipeline

docs, _ = get_pipeline().retrieve(
    "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
    k=20,
    rerank_top_k=5,
    enable_reranker=True,
)
print("documents:", len(docs))
print("top_ids:", [doc.metadata.get("id") for doc in docs[:5]])
PY
```

## CPU & Rollback Notes

- CPU inference works out of the box; reranking processes up to `reranker_max_candidates=10` candidates in batches of 8 before returning top 5 contexts.
- To disable reranking temporarily: set `PIPELINE_RERANKING=none`.
- To roll back the reranker checkpoint: repoint `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected` to `candidates/candidate-002-001`.
- To switch to zero-local-weight cloud inference: set `RUNTIME_PROFILE=cloud` with `JINA_API_KEY` and a populated `vietlaw_clauses_gemini` collection.
