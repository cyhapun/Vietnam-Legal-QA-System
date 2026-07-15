# Reranker Evaluation Dataset Recovery

Date: 2026-07-16

Status: blocked. The local machine does not currently contain enough raw or
prepared data to run Stage 2 reranker candidate evaluation without downloading
datasets again.

## Objective

Stage 2B traced the dataset provenance for the fine-tuned BGE reranker and
looked for local copies of the raw datasets, prepared train/validation/test
splits, and fixed candidate pools. No reranker candidate was evaluated or
selected during this stage.

## Notebook Provenance

Primary notebook:

`fine-tuning/reranking/notebooks/reranker_bge_v2_m3_finetuning.ipynb`

The notebook mounted Google Drive and used:

| Artifact | Notebook variable/code | Original path or source | Schema used | Expected rows | Save/export method |
| --- | --- | --- | --- | ---: | --- |
| Project workspace | `PROJECT_DIR` | `/content/drive/MyDrive/Project_ML` | N/A | N/A | Notebook working directory |
| Raw QA source 1 | `load_dataset("adamwhite625/vietnam-legal-qa", split="train")` | Hugging Face dataset | `question`, `law_content` | 4,837 after merge/dedup reports | Not saved locally by notebook |
| Raw QA source 2 | `load_dataset("huyydangg/LEGAL-EVAL-Dataset", split="test")` | Hugging Face dataset | `anchor`, `positive` | 3,806 after merge/dedup reports | Not saved locally by notebook |
| Raw QA source 3 | `load_dataset("thangvip/vietnamese-legal-qa", split="train")` | Hugging Face dataset | `generated_qa_pairs` containing `question`, `answer` | 29,137-29,138 in reports | Not saved locally by notebook |
| Prepared examples | `all_data` then split by positive passage group | In-memory notebook object | `query`, `pos`, `source` | 37,781 by split report | Not saved as dataset artifact |
| Train split | `train_data` | In-memory notebook object | `query`, `pos`, `source` | 26,446 | Not saved as dataset artifact |
| Validation split | `val_data` / `eval_val_data` | In-memory notebook object | `query`, `pos`, `source` | 5,667 | Not saved as dataset artifact |
| Test split | `test_data` / `eval_test_data` | In-memory notebook object | `query`, `pos`, `source` | 5,668 | Not saved as dataset artifact |
| Validation ranking negatives | `val_ranking_negatives` | In-memory TF-IDF output | 31 negatives per query | 5,667 pools | Not saved as candidate-pool artifact |
| Test ranking negatives | `test_ranking_negatives` | In-memory TF-IDF output | 31 negatives per query | 5,668 pools | Not saved as candidate-pool artifact |
| Model/report archive | shell `zip` command | `vietlaw-bge-reranker-v2-m3-finetuned.zip` | model checkpoints and report artifacts | N/A | `zip -r ... vietlaw-bge-reranker-v2-m3-finetuned/ report_artifacts/ training_log_history_raw.csv training_log_history_synced.csv` |

## Protocol

- Seed: `42`
- Split ratio: train `70%`, validation `15%`, test `15%`
- Split grouping key: normalized positive passage text
- Positive-passage normalization: strip, lowercase, collapse whitespace
- Pair deduplication: first `(query, positive)` pair retained
- Training negative strategy: TF-IDF hard negatives
- Training negatives per query: `3`
- Validation Trainer negatives per query: `3`
- Final validation/test ranking pool: one positive plus `31` TF-IDF hard negatives
- TF-IDF settings: `lowercase=True`, `max_features=100000`, `ngram_range=(1, 2)`, `min_df=2`
- Ranking metric used for checkpoint selection: `eval_mrr`
- `metric_for_best_model="eval_mrr"`, `greater_is_better=True`, `load_best_model_at_end=True`

## Report Evidence

The repository contains report artifacts for the BGE reranker, but not the raw
or prepared datasets needed to rerun evaluation.

| Artifact | Path | Classification | Size | SHA-256 | Usable for Stage 2 selection |
| --- | --- | --- | ---: | --- | --- |
| Split summary | `fine-tuning/reranking/results/bge-reranker-v2-m3/report_artifacts/table_2_split_summary.csv` | REPORT_ONLY | 211 bytes | `5b7235ea68b858aea6145be991c7948d4734649403557fd89eaf2a6a9e1d3fbb` | No |
| Source distribution | `fine-tuning/reranking/results/bge-reranker-v2-m3/report_artifacts/table_3_source_distribution.csv` | REPORT_ONLY | 138 bytes | `2ef7d9660aa383064a8618085ab26328a2b67a1fd21a0230bd1c9e6ebb5affe9` | No |
| Leakage summary | `fine-tuning/reranking/results/bge-reranker-v2-m3/report_artifacts/table_3_overlap_summary.csv` | REPORT_ONLY | 146 bytes | `5f7f578d748eed5d920cfc4b00702caca9fdc0c7fd01ae8776cd5f4a77cc7461` | No |
| Hyperparameters | `fine-tuning/reranking/results/bge-reranker-v2-m3/report_artifacts/table_7_hyperparameters.csv` | REPORT_ONLY | 436 bytes | `5e644344fcd892541e2b81742b2e33e9a0e9c1cb066d019a21a22699013dd786` | No |
| Training log | `fine-tuning/reranking/results/bge-reranker-v2-m3/report_artifacts/table_8a_training_log_raw.csv` | REPORT_ONLY | 2,058 bytes | `678c93310cefa2b8f3476ad276ef049a947dea6bdfc9cac4db0f880fd5463834` | No |
| Fine-tuned test metrics | `fine-tuning/reranking/results/bge-reranker-v2-m3/eval_reranker_finetuned/metrics.json` | REPORT_ONLY | 549 bytes | `01d54c96a230ee66ba180693a961214f73c5fe5f18cf57fb660ee7fe579cc61e` | No |
| Fine-tuned test error summary | `fine-tuning/reranking/results/bge-reranker-v2-m3/eval_reranker_finetuned/error_details.csv` | REPORT_ONLY | 13,741,951 bytes | `f47755c9215a7486c952f6781082626c586b740d102bf9746dd87a3dcaee94a6` | No |
| VnLaw-QA legal chunks | `/home/phat/AI_Project/VnLaw-QA/data/processed/legal_chunks.jsonl` | UNRELATED | 180,915,261 bytes | Not computed | No |
| VnLaw-QA priority chunks | `/home/phat/AI_Project/VnLaw-QA/artifacts/runs/chunking/priority/legal_chunks.jsonl` | UNRELATED | 49,945,533 bytes | Not computed | No |

The `error_details.csv` files contain query, positive passage, predicted top
passage, scores, rank, and candidate count. They do not contain the full 31
negative documents per query, so they cannot reconstruct fixed candidate pools.

## Search Locations Checked

Local checks were read-only and limited to project-related paths and filename
patterns:

- Repository working tree, excluding `.git`, virtual environments, frontend
  build output, node modules, and `models/`
- Git history across all local and remote refs for `fine-tuning/data` and
  `fine-tuning/reranking`
- Git object list and Git LFS metadata
- Git unreachable objects; the only unreachable blob was a small frontend merge
  conflict snippet, not data
- `/home/phat/AI_Project`
- `/home/phat/Downloads` and `/home/phat/Documents` if present
- `/mnt`, `/media`, and Windows user folders under `/mnt/c/Users/phatt`
- OneDrive folders under `/mnt/c/Users/phatt/OneDrive*`
- Hugging Face cache path patterns under `/home/phat/.cache/huggingface`

No exact prepared splits, no exact candidate pools, and no local export of the
three source Hugging Face datasets were found.

## Dataset Summary From Reports

| Split | Rows |
| --- | ---: |
| Train | 26,446 |
| Validation | 5,667 |
| Test | 5,668 |

| Source | Rows |
| --- | ---: |
| `thangvip/vietnamese-legal-qa` | 29,137-29,138 in available reports |
| `adamwhite625/vietnam-legal-qa` | 4,837 |
| `huyydangg/LEGAL-EVAL-Dataset` | 3,806 |

The small one-row discrepancy in the checked report artifacts is already present
in the repository reports: one split summary records test as `5,667`, while the
newer split summary and metrics record `5,668`. This cannot be resolved without
the underlying dataset.

## Leakage Evidence

Only the saved report can be checked locally:

| Overlap type | Count |
| --- | ---: |
| Train-Val query | 5 |
| Train-Test query | 6 |
| Val-Test query | 1 |
| Train-Val passage | 0 |
| Train-Test passage | 0 |
| Val-Test passage | 0 |

The mandatory Stage 2B leakage check cannot be recomputed because the local
train/validation/test rows and candidate pools are not present. The available
report suggests positive-passage group overlap was zero.

## Local Ignored Layout

If the dataset is recovered later, place or symlink local artifacts under:

```text
fine-tuning/data/local/reranker-evaluation/
├── train.jsonl
├── validation.jsonl
├── test.jsonl
├── validation_candidates.jsonl
├── test_candidates.jsonl
└── manifest.json
```

`fine-tuning/data/local/` is ignored by Git. The local `manifest.json` should
contain source paths, checksums, row counts, candidate-pool distributions, and
leakage results, but it must not be committed.

## Recovery Classification

Current classification:

- Exact prepared splits: not found
- Exact candidate pools: not found
- Raw source dataset exports: not found
- Report-only artifacts: found
- Unrelated legal corpus/chunking files: found in another project, not usable for
  reranker candidate evaluation

Decision:

`BLOCKED — DATASET NOT RECOVERABLE LOCALLY`

## Required Artifacts

Recover one of these sets before returning to Stage 2 candidate evaluation:

1. Exact prepared split/candidate artifacts:
   - `train.jsonl`
   - `validation.jsonl`
   - `test.jsonl`
   - `validation_candidates.jsonl` with one positive plus 31 negatives per query
   - `test_candidates.jsonl` with one positive plus 31 negatives per query
   - local manifest/checksums, if available

2. Or exact raw source exports sufficient to reconstruct deterministically:
   - `adamwhite625/vietnam-legal-qa` train split export
   - `huyydangg/LEGAL-EVAL-Dataset` test split export
   - `thangvip/vietnamese-legal-qa` train split export
   - evidence that row counts and schemas match the notebook run

The original Colab/Drive location to inspect is:

`/content/drive/MyDrive/Project_ML`

The notebook archive name to look for is:

`vietlaw-bge-reranker-v2-m3-finetuned.zip`

That archive, as shown by the notebook, included model checkpoints and report
artifacts. It may not include datasets unless they were manually exported
outside the visible notebook cells.

## Conditions To Resume Stage 2

Stage 2 evaluation can resume only after:

- validation/test splits are locally available;
- candidate pools are available or can be rebuilt deterministically from local
  raw data;
- candidate pools contain exactly one positive and up to 31 hard negatives per
  query;
- positive-passage group overlap across train/validation/test is zero;
- checksums and row counts are recorded in the ignored local manifest; and
- `fine-tuning/reranking/evaluate_candidates.py` can consume the local dataset
  without downloading anything.
