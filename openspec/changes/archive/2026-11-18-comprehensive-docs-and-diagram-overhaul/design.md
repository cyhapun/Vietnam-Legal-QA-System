# Design: Comprehensive Documentation, Architecture Diagram & Comment Cleanup

## Context

Per `.github/CONTRIBUTING.md`, all project documentation and developer-facing docs should be written in English. Recent architectural milestones (unified `RUNTIME_PROFILE=local|cloud`, Gemini Embedding + Jina Cross-Encoder Reranker, parallel Qdrant collection cloning, Vercel Services with `bindings`, and responsive mobile/tablet UI) left `README.md`, `docs/*`, `overview.png`, and various inline code comments outdated and verbose.

## Goals / Non-Goals

**Goals:**
- Replace the AI-generated `overview.png` with a clean, crisp, publication-grade architectural diagram authored in SVG (`docs/overview.svg`) and rendered to `overview.png` at 2x Retina resolution via headless Chrome (`3200x1840` or `3200x1760`).
- Consolidate and rewrite `README.md` in crisp, professional English (~300–400 lines, eliminating repetition and stale BYOK/Ollama/HF/deleted-fixture statements).
- Synchronize `docs/deployment-runtime-profiles.md`, `docs/local_model_integration.md`, `docs/legal_answer_quality_evaluation.md`, `docs/pipeline_latency_measurement.md`, and `fine-tuning/README.md` to English and to actual repo behavior.
- Clean up stale, verbose, or contradictory comments/docstrings in backend and frontend source files with **zero functional changes**.

**Non-Goals:**
- Deleting legacy compatibility adapters (`ollama.py`, `faiss_search.py`, `embedding_similarity.py`) or modifying runtime logic.
- Altering user-facing Vietnamese UI strings (which are intentionally Vietnamese for end users and checked by `verify-chat-ux.mjs`).
- Changing OpenSpec historical archives.

## Decisions

### 1. Vector-First Architecture Diagram (`docs/overview.svg` → `overview.png`)

- **Tooling**: Author a self-contained, responsive SVG (`viewBox="0 0 1600 900"`) using clean modern system typography (`Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`), crisp rounded cards, subtle architectural dot-grid background, distinct color coding for **Local Mode** (indigo/blue), **Cloud Mode** (emerald/teal), **Data Stores** (amber/slate), and **LLM/Validation** (violet/blue).
- **Rendering**: Render via local macOS headless Chrome (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --headless=new --screenshot=overview.png --window-size=1600,900 --force-device-scale-factor=2 --hide-scrollbars`) loading a zero-margin HTML wrapper embedding `docs/overview.svg` (or direct `file://` SVG), then visually inspect `overview.png` with `read_file` to verify alignment, spacing, legibility, and zero clipping/overlap.
- **Content structure (2 clean side-by-side panels)**:
  - **Left Panel (~34% width) — 1. Offline Ingestion & Cloud Clone**:
    - Legal Corpus JSON (`backend/data/processed/`, 8 Vietnamese laws · 5,758 clauses · 843 cross-refs)
    - `ClauseChunker` + Vietnamese BM25 Sparse Vectorizer
    - Dense Embeddings: Local `vietlaw-bge-m3` (`ingest_to_storage.py`) → `vietlaw_clauses` + Resumable Clone (`reindex_gemini_cloud.py`, Gemini `1024d`) → `vietlaw_clauses_gemini`
    - Storage Cylinders: **PostgreSQL / Supabase** (laws, clauses, sessions, feedback) & **Qdrant Cloud** (`text-dense` + `text-sparse` + keyword indexes) + Cache Invalidation.
  - **Right Panel (~66% width) — 2. Online RAG QA Pipeline**:
    - **Client & Gateway**: Next.js 15 Responsive UI (Mobile/Tablet/Desktop) ↔ FastAPI (`/chat/stream`, `/chat`, `/readiness`) via Vercel Services `bindings`
    - **Step 1 — Query Understanding**: LLM Query Rewriter (domain classification `legal`/`chitchat`, sub-queries, smart title) + Conversation Memory (Summary + last 4 turns)
    - **Step 2 — Semantic Cache**: Qdrant `semantic_cache` / `semantic_cache_gemini` (Hit → instant stream; Miss → RAG)
    - **Step 3 — Dual-Mode Hybrid Retrieval**: `RUNTIME_PROFILE=local` (BGE-M3 → `vietlaw_clauses`) vs. `cloud` (Gemini 1024d → `vietlaw_clauses_gemini`) + `law_id`/`category` metadata filter + Dense/Sparse RRF (`candidateK=20`)
    - **Step 4 — Dual-Mode Reranking (Top-10 → Top-5)**: `local` Fine-tuned `bge-reranker-v2-m3` vs. `cloud` **Jina Reranker v2** (`fail_open`)
    - **Step 5 — Context Assembly**: 2-Level Nested Context Builder (cross-references) + 6,000-token budget
    - **Step 6 — Generation & Guardrails**: Google AI Studio (`gemini-3.1-flash-lite` + Multi-Key & Model Fallback) → Deterministic Citation Validation (`<cite id="...">`) → SSE Stream / JSON
    - **Step 7 — Persistence & Memory**: Chat History (`postgres` or device-local `browser` mode) + Async Background Memory Summarizer.

### 2. Documentation Standardization (100% English)

- **`README.md`**: Clean, scannable engineering README in English (~300–380 lines):
  - Header + legal disclaimer + `![VietLaw AI RAG Pipeline Architecture](overview.png)` + team table + quick TOC
  - Key Highlights (Dual `local`/`cloud` switch, Hybrid Qdrant Retrieval + 2-level cross-reference context, Citation validation, Responsive Mobile/Tablet/Desktop UI)
  - Architecture & Pipeline summary (concise, referencing `overview.png` instead of duplicating bulky ASCII diagrams)
  - Project Structure (matching actual files in `backend/` and `frontend/`)
  - Quick Start (Local native, Docker Compose, Cloud mode + `reindex_gemini_cloud.py`, Vercel Services deployment)
  - Environment Configuration summary + Health/Readiness endpoints
  - Legal Corpus table (exact 8 Vietnamese laws, 5,756/5,758 clauses & 843 cross-references)
  - Testing & Verification (`pytest tests/`, `npm run verify:*`, `tsc --noEmit`)
  - Links to `docs/` guides + Known Limitations.
- **`docs/deployment-runtime-profiles.md`**: Updated to `RUNTIME_PROFILE=local|cloud` (`serverless` alias), Gemini + Jina cloud stack, parallel Qdrant collections, Vercel `services` + `bindings`, 5 required Vercel env vars, Supabase IPv4 pooler note, and `browser` vs `postgres` chat storage privacy guidance.
- **`docs/local_model_integration.md`**: Keep validated SHA-256 weight hashes, `models/` paths, `selected` symlink rollback, offline flags; update env snippets to `RUNTIME_PROFILE=local` and remove deleted `test_local_models_real.py` reference.
- **`docs/legal_answer_quality_evaluation.md` & `docs/pipeline_latency_measurement.md`**: Preserve factual metrics/methodology; note where historical fixtures were archived/removed and align runtime defaults (`RETRIEVER_CANDIDATE_K=20`, `reranker_max_candidates=10`, `topK=5`, `JinaReranker` timing support).
- **`fine-tuning/README.md`**: Translate concisely to English and update Qdrant/FAISS note.

### 3. Safe Inline Comment & Docstring Cleanup

- Strictly touch comments and docstrings—never alter executable statements, user-facing Vietnamese UI strings, log formats expected by tests, or strings checked by `frontend/scripts/verify-*.mjs`.
- Target files with stale/bloated comments identified in our audit:
  - Backend: `services/__init__.py`, `services/embedding/__init__.py`, `services/embedding/base.py`, `services/embedding/hf_endpoint.py`, `services/embedding/gemini.py`, `services/reranking/__init__.py`, `services/reranking/embedding_similarity.py`, `models.py`, `api/chat.py`, `services/chat_orchestrator.py`, `services/pipeline.py`, `services/storage.py`.
  - Frontend: `components/chat/ChatInterface.tsx`, `lib/constants.ts`, `hooks/use-chat-sessions.ts`.

## Risks / Trade-offs

- **Breaking `frontend/scripts/verify-*.mjs` or `pytest` during comment cleanup**: Mitigated by touching comments/docstrings only and running the entire backend (`43 pytest`) + frontend (`4 verify:*` + `tsc --noEmit`) suites immediately afterward.
- **SVG font fallback differences in headless Chrome**: Mitigated by using clean system sans-serif stack (`-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif`), generous padding inside every box, and inspecting the rendered `overview.png` directly via `read_file`.
