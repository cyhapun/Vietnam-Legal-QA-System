# Reranker Candidate Evaluation

Date: 2026-07-16

Status: blocked before model selection.

## Objective

Stage 2 is intended to choose one local fine-tuned reranker candidate using
validation metrics only, then evaluate the frozen winner once on a held-out test
set. The two local candidates are:

| Candidate | Path | SHA-256 |
| --- | --- | --- |
| candidate-002-001 | `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-002-001` | `6d15b6914846cd6ac1006badd256e325c93e80de975a26b46d647d7a51c0432e` |
| candidate-003-004 | `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-003-004` | `bdeb8e6771c7e97dd64136317c645529f10e4060c8e0578832f3dd1b6caa7079` |

Both candidates were previously validated offline as
`XLMRobertaForSequenceClassification` models with logits shape `(batch, 1)`.

## Fine-Tuning Protocol Audit

The relevant source notebook is:

`fine-tuning/reranking/notebooks/reranker_bge_v2_m3_finetuning.ipynb`

The notebook defines the BGE reranker experiment as:

- Base model: `BAAI/bge-reranker-v2-m3`
- Seed: `42`
- Split ratio: train `0.70`, validation `0.15`, test `0.15`
- Split strategy: group by normalized positive passage, then shuffle groups
- Training negatives per query: `3`
- Validation group negatives per query: `3`
- Final ranking negatives per query: `31`
- Ranking candidate count: `32` documents per query
- Negative strategy: TF-IDF hard negatives
- TF-IDF config: lowercase, max features `100000`, ngram range `(1, 2)`, `min_df=2`
- Training max length: `512`
- Validation checkpoint metric: `eval_mrr`
- `metric_for_best_model="eval_mrr"`
- `greater_is_better=True`
- `load_best_model_at_end=True`

The fine-tuning logs show the best validation metric:

| Step | Epoch | eval_mrr | eval_top1_accuracy | eval_loss |
| ---: | ---: | ---: | ---: | ---: |
| 2891 | 1.7489979581 | 0.9955149697 | 0.9911769896 | 0.0423877947 |
| 3304 | 1.9988656129 | 0.9955149697 | 0.9911769896 | 0.0429617465 |
| 3306 | 2.0 | 0.9954267396 | 0.9910005294 | 0.0429709703 |

`trainer_state.json` in `checkpoint-3306` points to
`./vietlaw-bge-reranker-v2-m3-finetuned/checkpoint-2891` as
`best_model_checkpoint`, but `checkpoint-2891` is not present in this repository.

## Existing Test Metrics From Notebook

The existing report artifacts contain held-out test metrics for the fine-tuned
BGE reranker, not a validation comparison between the two local candidate files:

| Metric | Fine-tuned BGE reranker |
| --- | ---: |
| MRR@10 | 0.984455968343583 |
| NDCG@10 | 0.9881716227342677 |
| Recall@1 | 0.9740649258997883 |
| Recall@3 | 0.9938249823570925 |
| Recall@5 | 0.9966478475652788 |
| Recall@10 | 0.9992942836979535 |
| MeanRank | 1.0601623147494708 |
| NumQueries | 5668 |
| CandidatesPerQuery | 32 |

These metrics cannot be used to choose between `candidate-002-001` and
`candidate-003-004` because they do not identify which local candidate file was
used and they are test metrics, not validation selection metrics.

## Dataset Availability

The notebook loads three Hugging Face datasets:

- `adamwhite625/vietnam-legal-qa`, split `train`
- `huyydangg/LEGAL-EVAL-Dataset`, split `test`
- `thangvip/vietnamese-legal-qa`, split `train`

Current repository state:

- `fine-tuning/data/synthetic/` contains only `.gitkeep`
- `fine-tuning/data/training/` contains only `.gitkeep`
- No local JSON/JSONL/Parquet train/validation/test datasets are present
- No local validation candidate pool artifact is present
- The Hugging Face dataset cache checked on this machine did not contain those datasets

Because the validation split and TF-IDF hard-negative pools cannot be recreated
offline from local artifacts, Stage 2 cannot select a final reranker without
violating the selection protocol.

## Leakage Checks

Only report artifacts can be audited locally. The notebook report records:

| Overlap type | Count |
| --- | ---: |
| Train-Val query | 5 |
| Train-Test query | 6 |
| Val-Test query | 1 |
| Train-Val passage | 0 |
| Train-Test passage | 0 |
| Val-Test passage | 0 |

This suggests the passage-group split reduced positive passage overlap to zero,
but a fresh leakage report cannot be recomputed without the original local
dataset.

## Reproducible Evaluation Script

Added:

`fine-tuning/reranking/evaluate_candidates.py`

The script supports:

- Multiple local candidate paths
- Validation or test split
- Offline mode by default
- Sequential model loading
- TF-IDF hard-negative candidate pools
- Shared candidate pools for all models
- Raw-logit ranking with stable sort
- MRR@10, NDCG@10, Recall@1/3/5/10, MeanRank, Top-1 metrics
- Per-query JSONL output
- Deterministic paired bootstrap

It requires a local JSONL dataset. Minimal schema:

```json
{"split":"validation","query_id":"q1","query":"...","positive_id":"p1","positive":"...","source":"..."}
```

Example validation command after restoring local data:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
python3 fine-tuning/reranking/evaluate_candidates.py \
  --dataset-jsonl fine-tuning/data/training/reranker_dataset.jsonl \
  --split validation \
  --candidate models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-002-001 \
  --candidate-name candidate-002-001 \
  --expected-sha256 candidate-002-001=6d15b6914846cd6ac1006badd256e325c93e80de975a26b46d647d7a51c0432e \
  --candidate models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-003-004 \
  --candidate-name candidate-003-004 \
  --expected-sha256 candidate-003-004=bdeb8e6771c7e97dd64136317c645529f10e4060c8e0578832f3dd1b6caa7079 \
  --output-dir fine-tuning/reranking/results/candidate_evaluation \
  --batch-size 8 \
  --max-length 512 \
  --device cpu
```

## Selection Decision

No candidate selected.

Reason: the validation dataset and fixed validation candidate pools needed for
fair selection are not available locally, and Stage 2 rules prohibit selecting
from smoke-test logits or held-out test metrics.

No `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected` symlink was
created.

## Required Recovery

Recover one of the following before reranker selection:

- The exact prepared reranker dataset with train/validation/test split and
  positive IDs/texts; or
- A local export of the three source datasets plus deterministic preprocessing
  output matching the notebook; and
- The fixed validation TF-IDF candidate pools if they were saved, or enough
  local data to rebuild them deterministically with the notebook protocol.

## Next Stage After Recovery

After validation data is restored:

1. Run candidate evaluation on validation only.
2. Select candidate by `eval_mrr`/MRR@10 and documented tie-breakers.
3. Create ignored symlink `models/.../selected` to the winner.
4. Evaluate only the selected candidate on held-out test.
5. Update this report and `models/ARTIFACT_MANIFEST.md`.
6. Proceed to Stage 3: versioned Qdrant/FAISS index migration and semantic cache rebuild.
