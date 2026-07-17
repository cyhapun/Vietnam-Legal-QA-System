# Deployment runtime profiles

The backend has two supported runtime profiles.

## Local/native or Docker

Use the fine-tuned filesystem models:

```env
RUNTIME_PROFILE=local
HUGGINGFACE_EMBEDDING_MODE=local
HUGGINGFACE_EMBEDDING_MODEL=../models/embedding/vietlaw-bge-m3-finetuned/best
PIPELINE_RERANKING=cross_encoder
LOCAL_MODELS_PRELOAD_ENABLED=true
LOCAL_MODELS_WARMUP_ENABLED=true
```

Install both dependency manifests:

```bash
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-local.txt
```

## Serverless deployment

Use the lightweight production dependency set and remote inference:

```env
RUNTIME_PROFILE=serverless
HUGGINGFACE_EMBEDDING_MODE=api
HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-m3
PIPELINE_RERANKING=embedding_similarity
LOCAL_MODELS_PRELOAD_ENABLED=false
LOCAL_MODELS_WARMUP_ENABLED=false
```

The serverless build installs only `backend/requirements.txt`. It must not
install `backend/requirements-local.txt`, PyTorch, Transformers, or
Sentence Transformers. A Hugging Face credential can be supplied by
`HUGGINGFACE_API_KEY` or by the browser request's runtime Hugging Face
credential; the request credential takes precedence for that request.

The deployed Qdrant collection must use the same 1024-dimensional BGE-M3
embedding space as the active embedding configuration.

## Verification and rollback

The change includes regression tests for profile validation, credential
routing, single-dispatch retrieval, remote reranking, and dependency
isolation. Static checks confirm that `vercel.json` is valid JSON, production
requirements exclude local ML packages, and the OpenSpec change validates.

Frontend production build verification passed with Next.js, including type
checking, static generation, and route tracing. The current workspace has no
installed Python runtime, Docker engine is unavailable, and the Vercel CLI is
not installed; therefore backend tests/import checks, package-size
verification, and local/Docker smoke tests must still run in a development or
CI environment before deployment.

If deployment verification fails, restore the previous runtime configuration
and dependency manifests. Do not use the serverless profile with local model
settings; run the local profile only on a runtime that includes the local
dependency manifest and model artifacts.
