# Deployment Runtime Profiles

The backend supports two unified runtime profiles controlled by a single environment variable: `RUNTIME_PROFILE=local` or `RUNTIME_PROFILE=cloud` (`serverless` is accepted as a backward-compatible alias normalized to `cloud`).

## Profile Matrix

| Component | `RUNTIME_PROFILE=local` | `RUNTIME_PROFILE=cloud` *(alias `serverless`)* |
|---|---|---|
| Embedding Provider | `huggingface` (`mode=local`) | `gemini` (`mode=api`) |
| Embedding Model | `../models/embedding/vietlaw-bge-m3-finetuned/best` | `models/gemini-embedding-001` (1024-dim) |
| Reranking Strategy | `cross_encoder` (local CPU/GPU) | `jina` (`jina-reranker-v2-base-multilingual`, `fail_open=true`) |
| LLM Provider | Google AI Studio (`GOOGLE_API_KEYS`) | Google AI Studio (`GOOGLE_API_KEYS`) |
| Qdrant Collection | `vietlaw_clauses` | `vietlaw_clauses_gemini` |
| Semantic Cache | `semantic_cache` | `semantic_cache_gemini` |
| Local Preload / Warm-up | `true` | `false` |

All profile-derived defaults remain overridable via explicit environment variables when needed.

---

## Local / Native or Docker Setup

Use the offline fine-tuned weights with zero cloud embedding/reranking cost:

```env
RUNTIME_PROFILE=local
GOOGLE_API_KEYS=your_google_api_key_1,your_google_api_key_2
POSTGRES_DSN=postgresql://postgres:postgres@localhost:15432/vietlaw
QDRANT_URL=http://localhost:6333
```

Install both base and local ML dependency manifests:

```bash
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-local.txt
```

See [`docs/local_model_integration.md`](local_model_integration.md) for local model directory paths and weight hashes.

---

## Cloud / Vercel Serverless Deployment

The cloud profile installs **only** `backend/requirements.txt` (excluding `torch`, `transformers`, and `sentence-transformers`) and starts in under 1 second.

### 1. Populate the Isolated Gemini Qdrant Collection

Local BGE-M3 vectors (`vietlaw_clauses`) and Gemini vectors (`vietlaw_clauses_gemini`) live in separate Qdrant collections so switching between `local` and `cloud` never corrupts retrieval.

Clone `vietlaw_clauses` → `vietlaw_clauses_gemini` safely using the resumable script:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/reindex_gemini_cloud.py --dry-run
PYTHONPATH=. .venv/bin/python scripts/reindex_gemini_cloud.py
```

The script reads `vietlaw_clauses` read-only, preserves `payload`, `text-sparse`, and keyword indexes (`category`, `law_id`), and skips point IDs already present in `vietlaw_clauses_gemini`. If Google Free Tier daily quota (1,000 RPD/key) is reached, re-run later or add keys to `GOOGLE_API_KEYS` to continue seamlessly.

### 2. Vercel Services Configuration (`vercel.json`)

`vercel.json` defines both services under the official Vercel `services` schema:

- **`frontend`**: Next.js 15 (`root: "frontend"`), wired to `backend` via a service binding that automatically injects `BACKEND_URL`.
- **`backend`**: FastAPI (`root: "backend"`), exposed under `/_/backend/:path*` via top-level `rewrites` (FastAPI strips the `/_/backend` mount prefix automatically in `backend/app/main.py`).
- Pre-configured environment defaults in `vercel.json`:
  - `RUNTIME_PROFILE=cloud`
  - `CHAT_STORAGE_MODE=browser`
  - `NEXT_PUBLIC_CHAT_STORAGE_MODE=browser`
  - `LOCAL_MODELS_PRELOAD_ENABLED=false`
  - `LOCAL_MODELS_WARMUP_ENABLED=false`

### 3. Required Vercel Environment Variables

Configure these 5 variables in **Vercel → Project Settings → Environment Variables**:

| Key | Purpose |
|---|---|
| `GOOGLE_API_KEYS` | Google AI Studio API key(s), comma-separated for automatic quota rotation |
| `JINA_API_KEY` | Jina AI API key(s) for `/v1/rerank` (`jina-reranker-v2-base-multilingual`) |
| `POSTGRES_DSN` | PostgreSQL/Supabase connection URI |
| `QDRANT_URL` | Qdrant Cloud endpoint (`https://...:6333`) |
| `QDRANT_API_KEY` | Qdrant Cloud API key |

> **Supabase IPv4 note on Vercel:** Direct Supabase hosts (`db.<project>.supabase.co:5432`) default to IPv6, whereas Vercel Serverless functions use IPv4. If `/_/backend/readiness` reports a PostgreSQL connection error, switch `POSTGRES_DSN` to Supabase's **Session or Transaction Pooler** URI (`aws-0-<region>.pooler.supabase.com`).

---

## Chat History Storage Modes

Chat persistence is independent from `STORAGE_BACKEND=qdrant_postgres`:

- **`browser` (recommended for public Vercel deployments)**: Sessions, messages, summaries, and feedback remain strictly in each user's browser `localStorage`. Users cannot view each other's conversations. History is device-local and not synced across browsers.
- **`postgres` (local development / trusted internal demos only)**: Persists chat history to PostgreSQL tables. Because user authentication is not configured, all visitors share the same history tables when `postgres` mode is enabled.

Both `CHAT_STORAGE_MODE` and `NEXT_PUBLIC_CHAT_STORAGE_MODE` must match; `validate_runtime_configuration()` fails fast if they diverge.

---

## Verification & Rollback

- Check `GET /health` for process liveness and `GET /readiness` (or `GET /_/backend/readiness` on Vercel) to confirm active profile, credentials, PostgreSQL, and Qdrant collection readiness.
- Run backend tests (`cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -q`) and frontend checks (`cd frontend && npm run verify:chat-ux && npm run verify:chat-storage`).
- To roll back locally from `cloud` to `local`, change only `RUNTIME_PROFILE=local` in `.env` and restart the backend; `vietlaw_clauses` remains untouched.
