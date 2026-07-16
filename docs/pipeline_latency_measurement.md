# Pipeline Latency Measurement

This instrumentation measures the current chat pipeline without changing retrieval,
reranking, model loading, prompts, semantic cache, or provider configuration.

## Enable Timing Logs

Timing is opt-in:

```bash
PIPELINE_TIMING_ENABLED=true
```

When disabled, the backend does not emit `pipeline_timing` logs and public API
responses/SSE events are unchanged.

## Stage Definitions

- `embedding_model_load`: lazy local embedding model initialization during the request.
- `reranker_model_load`: lazy local reranker tokenizer/model initialization during the request.
- `model_load`: sum of embedding and reranker model load durations.
- `query_embedding`: query vector inference only, excluding model load.
- `qdrant_search`: Qdrant request/response and conversion into runtime documents.
- `reranking`: tokenizer, cross-encoder inference, score extraction, and sorting, excluding model load.
- `context_building`: final context selection and prompt context construction.
- `llm_time_to_first_token`: provider request start to first streamed answer token.
- `llm_stream_after_first_token`: first streamed answer token to stream completion.
- `llm_generation`: provider request start to complete non-stream response or stream completion.
- `total_time_to_first_token`: API request start to first streamed answer token.
- `total`: API request start to response completion, error, or cancellation.

## Baseline Run

Use one Uvicorn worker and do not use `--reload`:

```bash
cd backend
PIPELINE_TIMING_ENABLED=true \
HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 \
.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1
```

By default, the backend preloads and warms the local embedding/reranker before
`/readiness` returns 200:

```bash
LOCAL_MODELS_PRELOAD_ENABLED=true
LOCAL_MODELS_WARMUP_ENABLED=true
```

`/health` remains fast while preload is running. `/readiness` may take around
90 seconds on the current CPU baseline, so deployment startup/readiness
timeouts should be greater than 120 seconds. Set either flag to `false` to
restore lazy request-time model loading for a specific run.

Keep the baseline configuration unchanged:

- local fine-tuned embedding;
- Qdrant Cloud collection;
- local fine-tuned reranker;
- retrieve 20 candidates;
- rerank 20 candidates;
- top 5 final contexts;
- semantic cache disabled;
- FAISS fallback disabled.

## Client Benchmark

In another terminal:

```bash
cd backend
.venv/bin/python scripts/benchmark_pipeline_latency.py \
  --base-url http://127.0.0.1:8000 \
  --endpoint /chat/stream \
  --timeout 300
```

The script prints request IDs. Correlate them with backend log lines where
`event` is `pipeline_timing`.

## Log Safety

Timing payloads include request ID, endpoint, outcome, cold/warm flags, config
shape, and durations. They must not include raw user questions, retrieved
context, answer text, API keys, database credentials, Qdrant keys, provider
headers, or local model absolute paths.

## Reports

Generated baseline reports belong outside Git, for example:

```bash
/tmp/vietlaw-pipeline-latency-baseline.md
```

Do not commit logs, reports, chat answers, credentials, or model artifacts.
