# Versioned Index Migration

This document describes the Stage 3 process for creating a new Qdrant
collection with the fine-tuned BGE-M3 embedding model and cutting local runtime
over safely.

## Collections

Use versioned names so the old index remains available for rollback:

```env
QDRANT_COLLECTION=vietlaw_clauses_bge_m3_ft_v1
SEMANTIC_CACHE_COLLECTION=semantic_cache_bge_m3_ft_v1
```

The previous collection, commonly `vietlaw_clauses`, must not be deleted or
recreated during migration. The previous semantic cache, commonly
`semantic_cache`, must not be cleared.

## Local Models

Host paths:

```text
models/embedding/vietlaw-bge-m3-finetuned/best
models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
```

Container paths:

```text
/models/embedding/vietlaw-bge-m3-finetuned/best
/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
```

`selected` currently points to `candidate-003-004` as a provisional runtime
candidate. This is not a validation-set selection result.

## Dry Run

Dry-run is read-only. It inventories the corpus, records the embedding artifact
hash, and reports the expected point count and batch count.

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/migrate_embedding_index.py \
  --dry-run \
  --source-corpus data/processed \
  --target-collection vietlaw_clauses_bge_m3_ft_v1 \
  --semantic-cache-collection semantic_cache_bge_m3_ft_v1 \
  --embedding-model ../models/embedding/vietlaw-bge-m3-finetuned/best \
  --embedding-dimension 1024 \
  --batch-size 32 \
  --device cpu \
  --report-path ../reports/index_migrations/vietlaw_clauses_bge_m3_ft_v1_dry_run.json
```

Reports under `reports/index_migrations/` are local artifacts and are ignored by
Git.

## Re-Index

Run the migration only against local Docker Compose Qdrant/PostgreSQL. Do not
run it against production or remote databases.

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
QDRANT_URL=http://localhost:6333 \
.venv/bin/python scripts/migrate_embedding_index.py \
  --resume \
  --source-corpus data/processed \
  --target-collection vietlaw_clauses_bge_m3_ft_v1 \
  --semantic-cache-collection semantic_cache_bge_m3_ft_v1 \
  --embedding-model ../models/embedding/vietlaw-bge-m3-finetuned/best \
  --embedding-dimension 1024 \
  --batch-size 32 \
  --device cpu \
  --report-path ../reports/index_migrations/vietlaw_clauses_bge_m3_ft_v1.json
```

The script:

- creates the target collection only when missing;
- never deletes or recreates an existing collection;
- uses named dense vector `text-dense` with dimension `1024` and cosine
  distance;
- uses sparse vector `text-sparse`;
- keeps the dummy default vector required by the current Qdrant query path;
- uses deterministic Qdrant point IDs derived from clause IDs;
- supports resume by skipping existing deterministic point IDs;
- validates finite vector values and dimensions before upsert;
- creates a new semantic cache collection when missing.

If the requested target collection exists with incompatible schema, the script
chooses the next versioned name such as `vietlaw_clauses_bge_m3_ft_v2` instead
of deleting the existing collection.

## Structural Validation

After migration, validate:

- target collection exists;
- `text-dense` dimension is `1024`;
- dense distance is cosine;
- sparse vector `text-sparse` exists;
- point count matches the expected corpus clause count;
- required payload fields exist: `id`, `law_id`, `law_name`, `content`,
  `category`, `position`, `cross_references`;
- migration report has `failed_points=0`;
- old collection point count and schema are unchanged.

## Retrieval Smoke

Run retrieval without calling an answer LLM. Use queries covering:

- land;
- housing;
- real estate business;
- notarization;
- construction;
- environment;
- civil procedure.

For each query, confirm that the new collection returns non-empty results and
that reranking through `/models/.../selected` preserves required metadata.

## Cutover

Only after migration and validation pass, update local runtime configuration:

```env
QDRANT_COLLECTION=vietlaw_clauses_bge_m3_ft_v1
SEMANTIC_CACHE_COLLECTION=semantic_cache_bge_m3_ft_v1
HUGGINGFACE_EMBEDDING_MODE=local
HUGGINGFACE_EMBEDDING_MODEL=/models/embedding/vietlaw-bge-m3-finetuned/best
PIPELINE_RERANKING=cross_encoder
RERANKER_MODEL=/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
```

Do not commit `.env`.

## Rollback

Rollback keeps both indexes intact:

1. Stop the backend.
2. Set `QDRANT_COLLECTION` back to the old collection.
3. Set `SEMANTIC_CACHE_COLLECTION` back to a cache compatible with that old
   embedding model.
4. Set embedding config back to the model used to build the old index if doing
   a full rollback.
5. Optionally set `PIPELINE_RERANKING=none`.
6. Restart backend and run retrieval smoke.

Do not delete either collection during rollback.

## FAISS

When `STORAGE_BACKEND=qdrant_postgres`, backend startup skips FAISS
initialization. The checked local FAISS index is therefore stale relative to the
fine-tuned embedding and must not be queried with fine-tuned query embeddings.

If FAISS fallback is required later, build a separate versioned FAISS index in
an ignored path and configure that path explicitly. Do not overwrite the current
FAISS directory.
