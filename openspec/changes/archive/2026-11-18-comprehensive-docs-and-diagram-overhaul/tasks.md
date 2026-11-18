# Implementation Tasks: Comprehensive Documentation, Architecture Diagram & Comment Cleanup

## 1. Architecture Diagram Redesign (`docs/overview.svg` & `overview.png`)
- [x] 1.1 Author a clean, high-precision English vector architecture diagram in `docs/overview.svg` covering Offline Ingestion / Cloud Clone and Online Dual-Mode RAG QA (`local` vs `cloud` Gemini + Jina + Qdrant + Supabase + Citation Validation + Memory).
- [x] 1.2 Render `overview.png` from `docs/overview.svg` at 2x Retina resolution using headless Chrome and visually inspect `overview.png` via `read_file` to confirm crisp typography, zero clipping/overlap, and zero typos.

## 2. Project Documentation Overhaul (100% English)
- [x] 2.1 Rewrite `README.md` in concise, accurate English synchronized with the live codebase (`RUNTIME_PROFILE=local|cloud`, Gemini + Jina, 8 legal codes, Vercel Services, Docker, responsive UI, real test commands).
- [x] 2.2 Update `docs/deployment-runtime-profiles.md` for unified `local`/`cloud` profiles, parallel Qdrant cloning, Vercel Services (`bindings`, 5 required env vars), and Supabase IPv4 pooler guidance.
- [x] 2.3 Update `docs/local_model_integration.md`, `docs/legal_answer_quality_evaluation.md`, `docs/pipeline_latency_measurement.md`, and `fine-tuning/README.md` to English and current repo state (preserving factual hashes and benchmark records).

## 3. Code Comment & Docstring Cleanup (Zero Behavioral Change)
- [x] 3.1 Clean up stale, verbose, or inaccurate docstrings/comments in `backend/app/` (`services/__init__.py`, `embedding/__init__.py`, `embedding/base.py`, `embedding/hf_endpoint.py`, `embedding/gemini.py`, `reranking/__init__.py`, `reranking/embedding_similarity.py`, `models.py`, `api/chat.py`, `services/chat_orchestrator.py`, `services/pipeline.py`, `services/storage.py`).
- [x] 3.2 Clean up stale or unaccented inline comments in `frontend/` (`components/chat/ChatInterface.tsx`, `lib/constants.ts`, `hooks/use-chat-sessions.ts`) without altering any UI text or behavior.

## 4. Verification
- [x] 4.1 Run full backend test suite (`pytest tests/`) and compile check (`python -m compileall app scripts tests -q`).
- [x] 4.2 Run all frontend verification scripts (`verify:chat-ux`, `verify:models`, `verify:inference-settings`, `verify:chat-storage`) and `npx tsc --noEmit`.
- [x] 4.3 Verify all internal links in `README.md` and `docs/` point to existing files and zero secrets appear in any diff.
