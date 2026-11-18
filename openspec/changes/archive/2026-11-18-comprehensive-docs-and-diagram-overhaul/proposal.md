# Proposal: Comprehensive Documentation, Architecture Diagram & Comment Cleanup

## Why

The repository's architecture has evolved substantially—moving to a unified `RUNTIME_PROFILE=local|cloud` switch (Local fine-tuned BGE-M3 + BGE-Reranker vs. Cloud Google Gemini Embedding + Jina AI Cross-Encoder Reranker), server-authoritative Google AI Studio LLM fallback, isolated parallel Qdrant collections (`vietlaw_clauses` vs. `vietlaw_clauses_gemini`), Vercel Services (`services` + `bindings` + `rewrites`), and a responsive mobile/tablet UI. However, project documentation, the architecture diagram, and many inline code comments are severely out of date and inconsistent with `.github/CONTRIBUTING.md`:

1. **`overview.png` is inaccurate and contains AI-generated typos**: It displays `"Otler việc"` on the semantic cache miss branch, omits `RUNTIME_PROFILE=local|cloud` (Gemini Embedding + Jina Reranker + isolated Qdrant collections), references removed Ollama/HuggingFace LLM routing, misorders law category filtering relative to Qdrant prefetch/RRF, and mixes fine-tuning cards into the online QA flow.
2. **Documentation contradicts the live codebase & mixes languages**: `README.md` (811 lines) still describes removed browser BYOK configuration, HuggingFace/Ollama chat models, wrong law category names, deleted test fixture paths (`backend/tests/fixtures/*.jsonl`), legacy `PIPELINE_REWRITER=none`, and appends an English section onto a Vietnamese README. `docs/deployment-runtime-profiles.md` still documents the broken HuggingFace Serverless API path instead of `RUNTIME_PROFILE=cloud` with Gemini + Jina. `.github/CONTRIBUTING.md` specifies English for all project and developer-facing documentation.
3. **Stale & verbose code comments**: Backend and frontend modules retain outdated docstrings/comments referencing Ollama/FAISS defaults, removed BYOK UI, legacy refactoring history, and unaccented Vietnamese shorthand notes.

## What Changes

- **Redesign `overview.png` (and store editable vector source `docs/overview.svg`)**:
  - Craft a clean, publication-grade English architectural diagram in SVG and render `overview.png` at 2x Retina resolution via headless Chrome.
  - Clearly depict both pipelines (**1. Offline Ingestion & Cloud Clone** and **2. Online RAG QA Pipeline**) with accurate stages: Query Rewriter (domain classification + smart title), Semantic Cache (hit/miss), Dual-Mode Retrieval (`local` BGE-M3 vs. `cloud` Gemini + `law_id`/`category` Qdrant filter + Dense/Sparse Hybrid RRF), Dual-Mode Reranking (`local` Cross-Encoder vs. `cloud` Jina Reranker v2), Nested 2-Level Context Builder + Token Budget, Google AI Studio LLM (Multi-Key & Multi-Model Fallback), Citation Validation & Sanitization, Chat Persistence (`postgres` vs. `browser`), and Background Memory Summarization.
- **Standardize all project documentation in concise, accurate English**:
  - Rewrite `README.md` to be concise, well-structured, and 100% aligned with the current codebase (dual-mode `local`/`cloud`, 8 real Vietnamese legal codes / 5,758 clauses, Vercel Services deployment, Docker Compose, responsive UI, real test & verification commands).
  - Update `docs/deployment-runtime-profiles.md` for `RUNTIME_PROFILE=local|cloud` (with `serverless` alias), Gemini + Jina cloud stack, parallel Qdrant cloning (`reindex_gemini_cloud.py`), Vercel 5-variable setup, and Supabase IPv4 pooler guidance.
  - Update `docs/local_model_integration.md`, `docs/legal_answer_quality_evaluation.md`, `docs/pipeline_latency_measurement.md`, and `fine-tuning/README.md` to remove broken file references and align config defaults while preserving factual hashes, methodology, and historical benchmarks.
- **Clean up stale & verbose comments/docstrings across `backend/app/` and `frontend/`**:
  - Trim obsolete refactor-history comments, fix inaccurate docstrings (Ollama/HF/BYOK/FAISS defaults), and standardize touched comments to concise English without changing runtime behavior or breaking any test or `verify:*` script.

## Capabilities

### New Capabilities
- `project-documentation`: Authoritative English documentation standards, editable vector architecture diagram (`docs/overview.svg` → `overview.png`), and clean inline code documentation aligned with the active runtime architecture.

## Impact

- **Diagram assets**: `docs/overview.svg` (new editable source), `overview.png` (replaced).
- **Documentation**: `README.md`, `docs/deployment-runtime-profiles.md`, `docs/local_model_integration.md`, `docs/legal_answer_quality_evaluation.md`, `docs/pipeline_latency_measurement.md`, `fine-tuning/README.md`.
- **Code comments only (zero behavioral change)**: `backend/app/services/__init__.py`, `backend/app/services/embedding/__init__.py`, `backend/app/services/embedding/hf_endpoint.py`, `backend/app/services/embedding/gemini.py`, `backend/app/services/reranking/embedding_similarity.py`, `backend/app/models.py`, `backend/app/api/chat.py`, `backend/app/services/chat_orchestrator.py`, `backend/app/services/pipeline.py`, `backend/app/services/storage.py`, `frontend/components/chat/ChatInterface.tsx`, `frontend/lib/constants.ts`, `frontend/hooks/use-chat-sessions.ts`.
- **Verification**: Full backend `pytest tests/` (43 tests) + all frontend `npm run verify:*` scripts + `npx tsc --noEmit` + visual inspection of rendered `overview.png`.
