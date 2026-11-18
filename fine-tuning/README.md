# Fine-Tuning Legal Retrieval Models

This directory contains notebooks and scripts for fine-tuning domain-specific Vietnamese legal retrieval models (Bi-Encoder embeddings and Cross-Encoder rerankers).

## Directory Structure

```text
fine-tuning/
├── data/
│   ├── synthetic/                    # LLM-generated query–clause QA pairs
│   └── training/                     # Formatted JSONL/CSV training splits
├── embedding/                        # Bi-Encoder fine-tuning (BAAI/bge-m3)
│   ├── notebooks/
│   │   ├── 01_data_generation.ipynb  # Generate synthetic legal queries per clause
│   │   ├── 02_finetune_bge_m3.ipynb  # Sentence-Transformers fine-tuning (MNRL loss)
│   │   └── 03_evaluation.ipynb       # Base vs. fine-tuned embedding comparison
│   └── scripts/                      # Server training scripts
├── reranking/                        # Cross-Encoder fine-tuning (BAAI/bge-reranker-v2-m3)
│   ├── notebooks/
│   │   ├── 01_data_preparation.ipynb # Mine hard-negative (query, doc) pairs from vector search
│   │   ├── 02_finetune_cross_encoder.ipynb
│   │   └── 03_evaluation.ipynb       # NDCG / MRR evaluation
│   └── scripts/                      # Server training scripts
└── README.md
```

## Workflow Summary

1. **Bi-Encoder Fine-Tuning (`embedding/`)**: Trains `BAAI/bge-m3` with Multiple Negatives Ranking Loss (MNRL) on `(query, positive_clause)` pairs to pull legal queries closer to exact statutory clauses while pushing non-relevant articles apart.
2. **Cross-Encoder Fine-Tuning (`reranking/`)**: Trains `BAAI/bge-reranker-v2-m3` with binary classification loss on `(query, clause, label)` pairs including hard negatives mined from dense retrieval, outputting calibrated relevance scores for top-K reranking.

For deploying trained artifacts locally in the backend, see [`../docs/local_model_integration.md`](../docs/local_model_integration.md).
