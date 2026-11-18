# Project Documentation & Architecture Diagram

## Purpose

Maintain concise, accurate, English-first project documentation, a crisp vector-backed system pipeline diagram (`docs/overview.svg` → `overview.png`), and clean non-redundant code comments synchronized with the live codebase.

## Requirements

### Requirement: Accurate vector-backed architecture diagram (`overview.png`)

The repository MUST provide an editable SVG diagram source (`docs/overview.svg`) and a high-resolution rendered `overview.png` in English that accurately reflects the active dual-mode RAG architecture with zero typos or obsolete components.

#### Scenario: Viewing `overview.png` in `README.md`

- **WHEN** a reader inspects `overview.png`
- **THEN** it clearly illustrates both the Offline Ingestion / Cloud Clone pipeline and the Online RAG QA pipeline
- **AND** it accurately shows `RUNTIME_PROFILE=local` (fine-tuned BGE-M3 + BGE-Reranker + `vietlaw_clauses`) and `RUNTIME_PROFILE=cloud` (Gemini Embedding + Jina Reranker v2 + `vietlaw_clauses_gemini`), Qdrant hybrid dense/sparse retrieval with metadata filtering, Nested Context Builder, Google AI Studio LLM fallback, Citation Validation, `postgres`/`browser` chat storage modes, and background memory summarization
- **AND** it contains zero typos and zero references to removed HuggingFace/Ollama chat routing

### Requirement: English-first, codebase-accurate Markdown documentation

`README.md`, `docs/*.md`, and `fine-tuning/README.md` MUST be written in concise, professional English per `.github/CONTRIBUTING.md` and accurately document only existing files, active defaults, and working commands.

#### Scenario: Following setup, deployment, or testing instructions in `README.md` and `docs/`

- **WHEN** a developer follows the documented Local, Docker, or Vercel deployment setup and test commands
- **THEN** every referenced script, environment variable, legal category, and test command exists and matches `backend/app/config.py`, `vercel.json`, `.env.example`, and `frontend/package.json`
- **AND** no documentation claims removed features such as browser BYOK provider switching or active HuggingFace Serverless API deployment

### Requirement: Concise, accurate inline comments and docstrings

Inline comments and module docstrings in `backend/app/` and `frontend/` MUST accurately describe current module responsibilities without obsolete refactor narratives, misleading legacy provider defaults, or behavioral regressions.

#### Scenario: Running automated verification after comment cleanup

- **WHEN** `pytest tests/`, `npm run verify:chat-ux`, `npm run verify:models`, `npm run verify:inference-settings`, `npm run verify:chat-storage`, and `npx tsc --noEmit` are executed after cleanup
- **THEN** all backend and frontend verification checks pass with zero regressions
