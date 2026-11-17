# Deployment Runtime Profiles

## Purpose

This capability defines compatible local and cloud (with `serverless` alias) runtime configurations
for inference, model loading, vector collection isolation, dependencies, and readiness checks.

## Requirements

### Requirement: Explicit runtime profile selection

The system MUST support a single minimal runtime profile toggle (`RUNTIME_PROFILE=local` or `RUNTIME_PROFILE=cloud`, with `serverless` accepted as a backward-compatible alias normalized to `cloud`), and each profile MUST automatically select compatible defaults for embedding, reranking, vector collections, semantic cache collection, and model preloading.

#### Scenario: Local profile uses fine-tuned artifacts and BGE-M3 collections

- **WHEN** the backend starts with `RUNTIME_PROFILE=local` (and no explicit component overrides)
- **THEN** it defaults to `EMBEDDING_PROVIDER=huggingface`, `HUGGINGFACE_EMBEDDING_MODE=local`, local fine-tuned BGE-M3 embedding artifact (`../models/embedding/vietlaw-bge-m3-finetuned/best`), local cross-encoder reranker (`../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected`), `QDRANT_COLLECTION=vietlaw_clauses`, `SEMANTIC_CACHE_COLLECTION=semantic_cache`, and `LOCAL_MODELS_PRELOAD_ENABLED=true`
- **AND** it does not require Hugging Face or Jina API credentials

#### Scenario: Cloud profile uses Gemini embedding, Jina reranker, and isolated Gemini collections

- **WHEN** the backend starts with `RUNTIME_PROFILE=cloud` or `RUNTIME_PROFILE=serverless` (and no explicit component overrides)
- **THEN** it normalizes the active profile to `cloud`
- **AND** it defaults to `EMBEDDING_PROVIDER=gemini` (`models/gemini-embedding-001`, 1024-dim), `PIPELINE_RERANKING=jina` (`jina-reranker-v2-base-multilingual`), `QDRANT_COLLECTION=vietlaw_clauses_gemini`, `SEMANTIC_CACHE_COLLECTION=semantic_cache_gemini`, and `LOCAL_MODELS_PRELOAD_ENABLED=false`
- **AND** it does not load local ML weights or require Hugging Face API credentials

#### Scenario: Incompatible profile configuration

- **WHEN** `RUNTIME_PROFILE=cloud` is missing `GOOGLE_API_KEYS` (when `EMBEDDING_PROVIDER=gemini`), or missing `JINA_API_KEY` (when `PIPELINE_RERANKING=jina`), or configured with a local-only artifact path
- **THEN** startup or readiness fails with a clear configuration error identifying the missing or incompatible setting without exposing credential values

### Requirement: Deployment dependency isolation

The system MUST provide a deployment dependency manifest that excludes local ML runtime packages and a local/Docker dependency path that installs the packages required by fine-tuned local inference.

#### Scenario: Serverless dependency installation

- **WHEN** the deployment platform installs the backend production requirements
- **THEN** the resulting dependency set does not include PyTorch, Transformers, Sentence Transformers, or local model weight runtimes that would inflate the serverless function bundle

#### Scenario: Local dependency installation

- **WHEN** a developer runs the documented local or Docker setup for the local profile
- **THEN** the base backend requirements and local ML extras are installed so the fine-tuned embedding and reranker can load successfully

### Requirement: Profile-aware readiness diagnostics

The system MUST report the active normalized runtime profile (`local` or `cloud`), embedding provider, reranker provider, and Qdrant collection, and validate only the resources required by that profile.

#### Scenario: Cloud readiness without local artifacts

- **WHEN** readiness is checked for `RUNTIME_PROFILE=cloud` with valid `GOOGLE_API_KEYS`, `JINA_API_KEY`, PostgreSQL, and Qdrant collection `vietlaw_clauses_gemini`
- **THEN** readiness reports `embedding.provider="gemini"`, `embedding.mode="api"`, `reranker.provider="jina"`, `reranker.mode="api"`, and `weights=false`
- **AND** readiness does not fail because local embedding or reranker artifact directories are absent

#### Scenario: Local readiness with missing artifact

- **WHEN** readiness is checked for `RUNTIME_PROFILE=local` and a required fine-tuned artifact is missing or incomplete
- **THEN** readiness reports a not-ready state with the artifact validation failure

### Requirement: Parallel Qdrant collection isolation and resumable cloning

The system MUST keep local BGE-M3 vectors and cloud Gemini vectors in separate Qdrant collections by default, and provide a safe clone-and-resume script to populate the Gemini collection without modifying the local BGE-M3 collection.

#### Scenario: Resumable Gemini collection cloning

- **WHEN** an operator runs `backend/scripts/reindex_gemini_cloud.py`
- **THEN** it reads source records from `vietlaw_clauses` without modifying `vietlaw_clauses`
- **AND** it creates the target collection `vietlaw_clauses_gemini` (if absent) with named vectors `text-dense` (1024-dim Cosine) and `text-sparse` (IDF) plus keyword payload indexes on `category` and `law_id`
- **AND** it skips point IDs that already exist in `vietlaw_clauses_gemini` so interrupted runs (e.g., hitting Google Free Tier 1,000 RPD) can resume safely without re-embedding completed points
