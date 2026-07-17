# Legal Answer Quality Evaluation

This document defines the evaluation workflow for improving legal answer
quality without changing the retrieval architecture, model weights, provider
model, API response schema, or SSE stream schema.

## Quality Stages

The evaluator separates quality into five stages:

1. Retrieval quality: whether an expected source appears in retrieved
   candidates.
2. Reranking quality: whether an expected source appears in the final top 5
   context.
3. Context quality: whether final context keeps source IDs, metadata, and
   non-empty legal text without duplicates.
4. Answer grounding: whether answer references are supported by final context.
5. Citation validity: whether cited IDs map to final context sources.

`top-5 overlap` can help detect broad behavior shifts, but it is not the main
quality metric.

## Dataset

The initial verified dataset is:

```text
backend/tests/fixtures/legal_retrieval_quality.jsonl
```

Each record has this shape:

```json
{
  "id": "land_transfer_conditions_001",
  "question": "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
  "required_source_ids": ["LDD_2024_D45_K1"],
  "acceptable_source_ids": [],
  "critical": true,
  "category": "land",
  "question_type": "natural_language",
  "notes": "Expected source verified against corpus metadata."
}
```

Ground-truth rules:

- Required and acceptable source IDs must exist in the tracked corpus.
- Direct citation examples may be derived from corpus metadata.
- Natural-language examples must be manually checked against clause text.
- Do not use Gemini or another model to generate ground truth.
- Do not include user logs or sensitive data.

The initial dataset includes the known land cases:

- `LDD_2024_D27_K3`
- `LDD_2024_D45_K1`

## Metrics

The evaluator reports:

- Retrieval Hit@10
- Retrieval Recall@10
- Reranker Hit@5
- Reranker Recall@5
- MRR@10
- critical miss count
- empty-context count
- duplicate final source count
- invalid citation count
- unsupported legal-reference count
- median total latency
- median TTFT when available

Failure stage values:

- `missing_from_corpus`
- `missing_from_qdrant_top10`
- `lost_during_reranking`
- `lost_during_context_building`
- `unused_by_answer`
- `invalid_citation`
- `passed`

## Running Retrieval Evaluation

Start the backend with the production-like local configuration. Keep:

- candidateK = 10
- topK = 5
- semantic cache disabled
- FAISS fallback disabled
- one Uvicorn worker
- no `--reload`

Then run from `backend/`:

```bash
.venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset tests/fixtures/legal_retrieval_quality.jsonl \
  --retrieval-only \
  --candidate-k 10 \
  --top-k 5 \
  --output /tmp/vietlaw-quality-improvements/phase0-baseline.json
```

The retrieval evaluator runs in-process and uses the existing pipeline. It
does not add a retrieval stage or change runtime behavior.

## Running Answer Evaluation

Answer evaluation calls the running backend `/chat` endpoint and should be
limited to representative questions to control provider cost:

```bash
.venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset tests/fixtures/legal_retrieval_quality.jsonl \
  --answer-evaluation \
  --base-url http://127.0.0.1:8000 \
  --max-questions 10 \
  --output /tmp/vietlaw-quality-improvements/phase0-answer.json
```

The evaluator stores IDs, counts, stage traces, and timing values. It does not
write full answers or passages to tracked paths.

## Corpus Integrity Audit

Run the read-only corpus audit from `backend/`:

```bash
.venv/bin/python scripts/audit_legal_corpus_integrity.py \
  --output /tmp/vietlaw-quality-improvements/corpus-integrity.json
```

The audit checks local JSON source IDs, empty text, malformed metadata, legal
identity collisions, and the known `LDD_2024_D27_K3` / `LDD_2024_D45_K1`
sources. It does not mutate PostgreSQL or Qdrant.

## Acceptance Thresholds

For behavior-changing phases:

- critical miss count must not increase;
- Retrieval Hit@10 must not decrease;
- Reranker Hit@5 must not decrease;
- MRR must not drop by more than 1%;
- invalid citations must not increase;
- unsupported legal references must not increase;
- empty context count must not increase;
- duplicate source count must not increase;
- median TTFT and total latency regression must stay within 10%.

Generated reports belong under `/tmp/vietlaw-quality-improvements/` and should
not be committed.

## Known Limitation

The known `LDD_2024_D45_K1` miss is a tracked retrieval-quality limitation.
This evaluation workflow makes that miss measurable, but it does not claim to
fix it unless a later accepted phase demonstrates improvement without
regression.
