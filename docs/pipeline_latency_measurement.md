# Pipeline Latency Measurement

Opt-in request-scoped timing instrumentation (`backend/app/services/pipeline_timing.py`) measures per-stage chat latency without logging user content, retrieved text, or credentials.

## Enabling Timing Logs

```env
PIPELINE_TIMING_ENABLED=true
```

When disabled (default), no `pipeline_timing` JSON events are emitted and API/SSE behavior is unchanged.

## Tracked Stages

- `embedding_model_load`: Lazy local embedding model initialization (0 ms when preloaded or in `cloud` mode).
- `reranker_model_load`: Lazy local reranker initialization (0 ms when preloaded or in `cloud` mode).
- `model_load`: Sum of embedding and reranker load times.
- `query_embedding`: Query vector inference (`vietlaw-bge-m3` local or `gemini-embedding-001` cloud).
- `qdrant_search`: Qdrant hybrid prefetch + RRF query and document mapping.
- `reranking`: Cross-encoder scoring and sorting (`CrossEncoderReranker` local or `JinaReranker` cloud).
- `context_building`: 2-level nested context expansion and token-budget pruning.
- `llm_time_to_first_token`: LLM request start to first streamed token.
- `llm_stream_after_first_token`: First streamed token to completion.
- `llm_generation`: Full LLM response duration.
- `total_time_to_first_token` / `total`: End-to-end API latency.

## Running a Benchmark

Start the backend with one Uvicorn worker (no `--reload`) and `PIPELINE_TIMING_ENABLED=true`:

```bash
cd backend
PIPELINE_TIMING_ENABLED=true PYTHONPATH=. .venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

In a second terminal, run the client benchmark:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/benchmark_pipeline_latency.py \
  --base-url http://127.0.0.1:8000 \
  --endpoint /chat/stream \
  --timeout 300
```

Correlate the printed `request_id` values with backend log lines where `"event": "pipeline_timing"`.

> **Runtime defaults:** Hybrid search fetches `RETRIEVER_CANDIDATE_K=20` candidates and caps reranking at `reranker_max_candidates=10` before returning `RETRIEVER_K=5` final clauses. In `RUNTIME_PROFILE=local`, preload/warm-up shifts ~80–90 s of CPU model loading into startup so the first user query reports `model_load=0`. In `RUNTIME_PROFILE=cloud`, cold start is < 1 s and reranking via Jina Reranker v2 typically completes in < 1 s.

## Historical CPU Optimization Summary (`local` Profile)

Reducing reranker candidate workload from 20 to 10 on the baseline CPU machine yielded:

- Warm reranking median: `59.54s → 40.30s`
- Warm total median: `73.89s → 51.47s`
- Warm TTFT median: `73.01s → 50.94s`

## Log Safety & Report Storage

Timing payloads contain only request metadata, config shapes, and millisecond durations—never raw prompts, answers, legal passages, API keys, or DSNs. Store generated benchmark reports outside Git (e.g., `/tmp/vietlaw-pipeline-latency.md`).
