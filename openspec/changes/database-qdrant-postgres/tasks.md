## 1. Infrastructure Setup

- [ ] 1.1 Add Qdrant and PostgreSQL service definitions to docker-compose.yml
- [ ] 1.2 Add connection and storage configuration variables to backend configuration
- [ ] 1.3 Add Python dependencies for Qdrant and PostgreSQL clients

## 2. Data Model and Schema

- [ ] 2.1 Define PostgreSQL schema for laws, clauses, and ingestion state
- [ ] 2.2 Define ingestion and indexing metadata models for backend use
- [ ] 2.3 Create bootstrap/init scripts for local development

## 3. Ingestion Pipeline

- [ ] 3.1 Implement document normalization and clause extraction from processed JSON
- [ ] 3.2 Implement PostgreSQL persistence for legal documents and clause records
- [ ] 3.3 Implement Qdrant upsert workflow for clause embeddings and metadata
- [ ] 3.4 Add support for incremental reindexing and idempotent ingestion

## 4. Retrieval Integration

- [ ] 4.1 Introduce a storage abstraction interface for vector and metadata access
- [ ] 4.2 Replace the current FAISS-backed retrieval path with the new abstraction
- [ ] 4.3 Preserve existing category filtering and context-building behavior
- [ ] 4.4 Add fallback behavior for development when database services are unavailable

## 5. Validation and Rollout

- [ ] 5.1 Validate end-to-end retrieval with sample legal questions
- [ ] 5.2 Update README and local setup instructions for Qdrant/PostgreSQL
- [ ] 5.3 Verify docker-compose startup and initial data ingestion flow
