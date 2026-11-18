# Legal Answer Quality Evaluation

This guide documents the evaluation workflow for measuring retrieval recall, reranking precision, citation grounding, and safe insufficient-context handling across the VietLaw AI pipeline.

## Quality Stages

`backend/scripts/evaluate_legal_quality.py` evaluates five pipeline stages independently:

1. **Retrieval quality**: Whether expected source IDs appear in retrieved candidates.
2. **Reranking quality**: Whether expected source IDs survive reranking into the final top-5 context.
3. **Context quality**: Whether final context preserves non-empty legal text, metadata, and unique source IDs.
4. **Answer grounding**: Whether legal claims and references are supported by final context.
5. **Citation validity**: Whether `<cite id="...">` markers map strictly to final context sources.

## Dataset Schema

Evaluation datasets are JSONL files (supply via `--dataset <path>`). Each record uses:

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

Insufficient-context records omit required IDs and declare:

```json
{
  "required_source_ids": [],
  "acceptable_source_ids": [],
  "expected_behavior": "insufficient_context",
  "must_not_invent_citation": true
}
```

> **Note:** Keep private evaluation datasets and generated JSON reports outside the repository (e.g., `/tmp/vietlaw-quality-evaluation/`). Ground-truth IDs must be manually verified against `backend/data/processed/*.json`, never synthesized by an LLM.

## Running Evaluations

### 1. Corpus Integrity Audit (Read-Only)

Validates all JSON source IDs, empty content, metadata structure, and ID uniqueness without mutating PostgreSQL or Qdrant:

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/audit_legal_corpus_integrity.py \
  --output /tmp/vietlaw-corpus-integrity.json
```

### 2. Retrieval-Only Evaluation

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset /path/to/legal_retrieval_quality.jsonl \
  --retrieval-only \
  --candidate-k 20 \
  --top-k 5 \
  --output /tmp/vietlaw-retrieval-eval.json
```

### 3. End-to-End Answer Evaluation

With the backend running at `http://127.0.0.1:8000` (single Uvicorn worker, semantic cache disabled for deterministic runs):

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset /path/to/legal_retrieval_quality.jsonl \
  --answer-evaluation \
  --base-url http://127.0.0.1:8000 \
  --max-questions 10 \
  --output /tmp/vietlaw-answer-eval.json
```

### 4. End-to-End Ragas Evaluation (`backend/evaluation/`)

```bash
cd backend
pip install -r evaluation/requirements.txt
python evaluation/prepare_dataset.py
python evaluation/evaluate.py
```

## Citation Sanitization Behavior

Generated answers pass through deterministic validation (`backend/app/services/answer_validation.py`):

- Citation IDs present in the final top-5 context are preserved.
- Invalid or hallucinated citation markers are stripped from the finalized answer.
- If a legal answer contains only invalid citations, the backend returns a concise insufficient-context fallback.
- For SSE streaming, tokens emitted prior to completion cannot be retracted, while the `done` event, persisted database record, and chat history always use the sanitized answer.

## Historical Reference Baseline (20-Record Local Fixture)

On the 20-record retrieval fixture and 18-answer manual review rubric (local fine-tuned BGE-M3 + BGE-Reranker):

| Metric | Recorded Value |
|---|---:|
| Retrieval Hit@10 / Recall@10 | 1.00 / 1.00 |
| Reranker Hit@5 / Recall@5 | 1.00 / 1.00 |
| MRR@10 | 0.6108 |
| Critical retrieval misses / Empty contexts / Duplicates | 0 / 0 / 0 |
| Required citation presence (16 answer runs) | 0.9375 |
| Invalid citations in final answer | 0 |
| Insufficient-context safe fallback (4 cases × 2 runs) | 8 / 8 |
| Manual rubric average score (18 answers, 0–2 scale) | 1.94 / 2.00 |

These numbers reflect a small curated fixture set and should not be interpreted as generalized legal accuracy across all Vietnamese legislation.
