# Local Model Integration

This backend can run the fine-tuned retrieval models from the local filesystem
without Hugging Face Hub or Hugging Face Inference API fallback in local mode.

## Artifacts

Expected host paths:

- Embedding: `models/embedding/vietlaw-bge-m3-finetuned/best`
- Reranker candidate 002-001: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-002-001`
- Reranker candidate 003-004: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-003-004`
- Provisional reranker runtime path: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected`

Expected Docker container paths:

- Embedding: `/models/embedding/vietlaw-bge-m3-finetuned/best`
- Reranker candidates under `/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/`
- Provisional reranker runtime path: `/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected`

The `models/` directory is ignored by Git and must not be committed. Docker
Compose mounts it read-only into the backend and ingest containers.

`candidate-003-004` is currently used as a provisional runtime candidate through
the ignored local `selected` symlink. This is an operational choice based on
artifact compatibility and offline smoke inference only. It is not a
validation-set comparison and must not be described as the best checkpoint.
`candidate-002-001` remains available for rollback.

Current validated weight hashes:

- Embedding `model.safetensors`: `a318ac316747eab2d429692a84d17ff25f038cb3b182f159ee97e313034a0e02`
- Reranker candidate 002-001 `model.safetensors`: `6d15b6914846cd6ac1006badd256e325c93e80de975a26b46d647d7a51c0432e`
- Reranker candidate 003-004 `model.safetensors`: `bdeb8e6771c7e97dd64136317c645529f10e4060c8e0578832f3dd1b6caa7079`

## Configuration

Embedding:

```env
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODE=local
HUGGINGFACE_EMBEDDING_MODEL=models/embedding/vietlaw-bge-m3-finetuned/best
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32
EMBEDDING_DIMENSION=1024
EMBEDDING_NORMALIZE=true
LOCAL_MODELS_OFFLINE=true
```

Reranker:

```env
PIPELINE_RERANKING=cross_encoder
RERANKER_MODEL=models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
RERANKER_DEVICE=cpu
RERANKER_BATCH_SIZE=8
RERANKER_MAX_LENGTH=512
RERANKER_FAIL_OPEN=false
LOCAL_MODELS_OFFLINE=true
```

The backend should reference the stable `selected` path instead of a concrete
candidate directory. Switch or rollback candidates by repointing the ignored
local symlink, for example from `candidate-003-004` to `candidate-002-001`.
Do not treat smoke-test logits as a model-selection result; the best reranker
still requires evaluation on a representative validation set. See
`docs/reranker_candidate_evaluation.md` for the current selection status.

## Local-Only Behavior

When `LOCAL_MODELS_OFFLINE=true`, the runtime sets `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` if they are not already set. Local embedding mode loads
with `SentenceTransformer(..., local_files_only=True)`. Local reranking loads
with `AutoTokenizer.from_pretrained(..., local_files_only=True)` and
`AutoModelForSequenceClassification.from_pretrained(..., local_files_only=True)`.

There is no Hugging Face API fallback for `PIPELINE_RERANKING=cross_encoder`.
If the local artifact is missing or invalid, startup/request handling raises a
clear error instead of converting the path into a Hub model id.

## Validation

Validate embedding only:

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/validate_local_models.py \
  --embedding-path ../models/embedding/vietlaw-bge-m3-finetuned/best \
  --skip-reranker
```

Validate a reranker candidate:

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/validate_local_models.py \
  --skip-embedding \
  --reranker-path ../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
```

Real-model pytest coverage is opt-in:

```bash
cd backend
RUN_LOCAL_MODEL_TESTS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 pytest tests/test_local_models_real.py
```

## Index and Cache Consistency

The embedding dimension is configured by `EMBEDDING_DIMENSION` and is used by
the main Qdrant dense vector and semantic cache collection. Existing Qdrant
collections with a different dimension now raise a migration error; they are
not recreated automatically.

Semantic cache collection name is configured independently with
`SEMANTIC_CACHE_COLLECTION`. Use a new cache collection when switching to a new
embedding index, for example `semantic_cache_bge_m3_ft_v1`.

Changing the embedding model requires a migration stage:

- Re-index Qdrant with the new embedding model.
- Rebuild FAISS if FAISS fallback is used.
- Clear or rebuild semantic cache.
- Avoid querying a pretrained-model index with fine-tuned query embeddings.

See `docs/versioned_index_migration.md` for the versioned Qdrant migration,
cutover, and rollback procedure.

This stage does not re-index, clear cache, or mutate production data.

## CPU and GPU Notes

CPU inference works but can be slow, especially reranking with
`candidateK=60`. Lower `RERANKER_BATCH_SIZE`, `RERANKER_MAX_LENGTH`, or the
retrieval candidate count if latency or RAM usage is too high. GPU can be used
by changing `EMBEDDING_DEVICE` and `RERANKER_DEVICE`, but Docker images should
not pin CUDA-specific local builds in the shared dependency manifest.

## Rollback

- Disable reranking with `PIPELINE_RERANKING=none`.
- Repoint `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected` to
  `candidates/candidate-002-001` if the provisional candidate performs poorly
  in real use.
- Point embedding and collection configuration back to the previous model/index
  pair before serving traffic.
- Do not reuse semantic cache entries across embedding model changes.
