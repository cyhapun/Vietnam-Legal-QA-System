#!/usr/bin/env python3
"""Evaluate local reranker candidates on fixed validation/test candidate pools.

This script intentionally does not download datasets or models. Provide a local
JSONL dataset with at least: split, query, positive. Optional fields:
query_id, positive_id, source. Candidate pools are deterministically rebuilt per
split using the same TF-IDF hard-negative strategy documented in the fine-tuning
notebook.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


REQUIRED_MODEL_FILES = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
)

DEFAULT_EXPECTED_HASHES = {
    "candidate-002-001": "6d15b6914846cd6ac1006badd256e325c93e80de975a26b46d647d7a51c0432e",
    "candidate-003-004": "bdeb8e6771c7e97dd64136317c645529f10e4060c8e0578832f3dd1b6caa7079",
}


@dataclass(frozen=True)
class Example:
    query_id: str
    query: str
    positive_id: str
    positive: str
    split: str
    source: str = ""


@dataclass(frozen=True)
class CandidatePool:
    query_id: str
    query: str
    positive_id: str
    positive: str
    candidates: Tuple[Tuple[str, str], ...]
    positive_index: int


def set_offline_env() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def normalize_text(text: Any) -> str:
    return " ".join(str(text or "").strip().lower().split())


def clean_text(text: Any) -> str:
    if isinstance(text, (list, tuple)):
        text = " ".join(str(item) for item in text)
    return str(text or "").strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checksum_paths(paths: Sequence[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p)):
        h.update(str(path).encode("utf-8"))
        h.update(b"\0")
        h.update(sha256_file(path).encode("ascii"))
        h.update(b"\0")
    return h.hexdigest()


def load_jsonl_dataset(path: Path) -> List[Example]:
    examples: List[Example] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            query = clean_text(row.get("query") or row.get("question"))
            positive = clean_text(row.get("positive") or row.get("pos") or row.get("positive_passage"))
            split = clean_text(row.get("split")).lower()
            if not split:
                raise ValueError(f"{path}:{line_no} missing split")
            if not query or not positive:
                raise ValueError(f"{path}:{line_no} missing query or positive")
            examples.append(
                Example(
                    query_id=clean_text(row.get("query_id") or row.get("id") or f"{split}-{line_no}"),
                    query=query,
                    positive_id=clean_text(row.get("positive_id") or hashlib.sha1(positive.encode("utf-8")).hexdigest()),
                    positive=positive,
                    split=split,
                    source=clean_text(row.get("source")),
                )
            )
    return examples


def split_by_passage_group(
    examples: Sequence[Example],
    train_size: float = 0.70,
    val_size: float = 0.15,
    seed: int = 42,
) -> Dict[str, List[Example]]:
    rng = random.Random(seed)
    groups: Dict[str, List[Example]] = {}
    for item in examples:
        groups.setdefault(normalize_text(item.positive), []).append(item)

    grouped = list(groups.values())
    rng.shuffle(grouped)
    total = len(examples)
    targets = {
        "train": int(total * train_size),
        "validation": int(total * val_size),
        "test": total - int(total * train_size) - int(total * val_size),
    }
    splits = {"train": [], "validation": [], "test": []}
    for group in grouped:
        best_split = min(splits, key=lambda name: len(splits[name]) / max(targets[name], 1))
        splits[best_split].extend(group)
    for values in splits.values():
        rng.shuffle(values)
    return splits


def deduplicate_pairs(examples: Sequence[Example]) -> List[Example]:
    seen = set()
    deduped = []
    for item in examples:
        key = (normalize_text(item.query), normalize_text(item.positive))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def dataset_report(splits: Dict[str, Sequence[Example]]) -> Dict[str, Any]:
    report: Dict[str, Any] = {"splits": {}, "overlap": {}, "empty": {}}
    for name, items in splits.items():
        query_norms = [normalize_text(x.query) for x in items]
        pos_norms = [normalize_text(x.positive) for x in items]
        report["splits"][name] = {
            "queries": len(items),
            "unique_queries": len(set(query_norms)),
            "unique_positive_ids": len({x.positive_id for x in items}),
            "unique_positive_texts": len(set(pos_norms)),
        }
        report["empty"][name] = {
            "empty_queries": sum(not x.query for x in items),
            "empty_positives": sum(not x.positive for x in items),
        }

    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        left_items = splits.get(left, [])
        right_items = splits.get(right, [])
        report["overlap"][f"{left}_{right}_query"] = len(
            {normalize_text(x.query) for x in left_items} & {normalize_text(x.query) for x in right_items}
        )
        report["overlap"][f"{left}_{right}_positive_id"] = len(
            {x.positive_id for x in left_items} & {x.positive_id for x in right_items}
        )
        report["overlap"][f"{left}_{right}_positive_text"] = len(
            {normalize_text(x.positive) for x in left_items} & {normalize_text(x.positive) for x in right_items}
        )
    return report


def assert_no_blocking_leakage(report: Dict[str, Any]) -> None:
    positive_leaks = {
        key: value
        for key, value in report.get("overlap", {}).items()
        if ("positive_id" in key or "positive_text" in key) and value
    }
    if positive_leaks:
        raise RuntimeError(f"Positive document leakage detected: {positive_leaks}")


def random_negatives_for_index(
    idx: int,
    examples: Sequence[Example],
    num_negatives: int,
    rng: random.Random,
) -> List[Example]:
    positive = examples[idx].positive
    negatives: List[Example] = []
    attempts = 0
    while len(negatives) < num_negatives and attempts < 1000:
        j = rng.randrange(len(examples))
        candidate = examples[j]
        if j != idx and candidate.positive != positive and candidate not in negatives:
            negatives.append(candidate)
        attempts += 1
    if len(negatives) < num_negatives:
        for j, candidate in enumerate(examples):
            if j != idx and candidate.positive != positive and candidate not in negatives:
                negatives.append(candidate)
                if len(negatives) == num_negatives:
                    break
    return negatives


def build_tfidf_negatives(
    examples: Sequence[Example],
    num_negatives: int,
    top_k_pool: int = 100,
    seed: int = 65,
    batch_size: int = 128,
) -> List[List[Example]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np

    rng = random.Random(seed)
    queries = [x.query for x in examples]
    passages = [x.positive for x in examples]
    n = len(examples)
    if n <= 1:
        return [[] for _ in examples]

    vectorizer = TfidfVectorizer(lowercase=True, max_features=100_000, ngram_range=(1, 2), min_df=2)
    doc_matrix = vectorizer.fit_transform(passages)
    query_matrix = vectorizer.transform(queries)
    k = min(top_k_pool + 1, n)
    all_negatives: List[List[Example]] = []
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        sims = query_matrix[start:end].dot(doc_matrix.T).toarray()
        for local_i, scores in enumerate(sims):
            idx = start + local_i
            positive = passages[idx]
            if k < n:
                candidate_idx = np.argpartition(-scores, kth=k - 1)[:k]
            else:
                candidate_idx = np.arange(n)
            candidate_idx = candidate_idx[np.argsort(-scores[candidate_idx])]
            negatives: List[Example] = []
            for j in candidate_idx:
                j = int(j)
                candidate = examples[j]
                if j != idx and candidate.positive != positive and candidate not in negatives:
                    negatives.append(candidate)
                if len(negatives) == num_negatives:
                    break
            if len(negatives) < num_negatives:
                for candidate in random_negatives_for_index(idx, examples, num_negatives - len(negatives), rng):
                    if candidate not in negatives:
                        negatives.append(candidate)
                    if len(negatives) == num_negatives:
                        break
            all_negatives.append(negatives)
    return all_negatives


def build_candidate_pools(
    examples: Sequence[Example],
    negatives: Sequence[Sequence[Example]],
    seed: int = 42,
) -> List[CandidatePool]:
    if len(examples) != len(negatives):
        raise ValueError("examples and negatives must have the same length")
    rng = random.Random(seed)
    pools: List[CandidatePool] = []
    for idx, item in enumerate(examples):
        entries = [(item.positive_id, item.positive)]
        seen = {item.positive}
        for neg in negatives[idx]:
            if neg.positive not in seen:
                entries.append((neg.positive_id, neg.positive))
                seen.add(neg.positive)
        if len(entries) < 2:
            raise ValueError(f"candidate pool for query {item.query_id} is empty or lacks negatives")
        order = list(range(len(entries)))
        rng.shuffle(order)
        shuffled = tuple(entries[i] for i in order)
        pools.append(
            CandidatePool(
                query_id=item.query_id,
                query=item.query,
                positive_id=item.positive_id,
                positive=item.positive,
                candidates=shuffled,
                positive_index=order.index(0),
            )
        )
    return pools


def rank_positive(scores: Sequence[float], positive_index: int) -> Tuple[int, int]:
    if not scores:
        raise ValueError("scores must not be empty")
    if positive_index >= len(scores):
        raise ValueError("positive_index out of range")
    indexed_scores = list(enumerate(scores))
    indexed_scores.sort(key=lambda item: (-item[1], item[0]))
    sorted_indices = [idx for idx, _ in indexed_scores]
    return sorted_indices.index(positive_index) + 1, sorted_indices[0]


def compute_metrics(ranks: Sequence[int], candidates_per_query: int) -> Dict[str, float]:
    if not ranks:
        raise ValueError("ranks must not be empty")
    n = len(ranks)
    top1 = sum(rank == 1 for rank in ranks)
    metrics = {
        "MRR@10": sum((1.0 / rank) if rank <= 10 else 0.0 for rank in ranks) / n,
        "NDCG@10": sum((1.0 / math.log2(rank + 1)) if rank <= 10 else 0.0 for rank in ranks) / n,
        "Recall@1": sum(rank <= 1 for rank in ranks) / n,
        "Recall@3": sum(rank <= 3 for rank in ranks) / n,
        "Recall@5": sum(rank <= 5 for rank in ranks) / n,
        "Recall@10": sum(rank <= 10 for rank in ranks) / n,
        "MeanRank": sum(ranks) / n,
        "MedianRank": statistics.median(ranks),
        "NumQueries": n,
        "CandidatesPerQuery": candidates_per_query,
        "Top1_Accuracy": top1 / n,
        "Top1_Precision": top1 / n,
        "Top1_Recall": top1 / n,
        "Top1_F1": top1 / n,
        "PositiveMissingTop10": sum(rank > 10 for rank in ranks),
    }
    return {key: float(value) if isinstance(value, int) and key not in {"NumQueries", "CandidatesPerQuery", "PositiveMissingTop10"} else value for key, value in metrics.items()}


def paired_bootstrap(
    left_values: Sequence[float],
    right_values: Sequence[float],
    seed: int = 42,
    samples: int = 1000,
) -> Dict[str, float]:
    if len(left_values) != len(right_values) or not left_values:
        raise ValueError("paired bootstrap inputs must be non-empty and equal length")
    rng = random.Random(seed)
    diffs = [right - left for left, right in zip(left_values, right_values)]
    observed = sum(diffs) / len(diffs)
    boot = []
    for _ in range(samples):
        draw = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        boot.append(sum(draw) / len(draw))
    boot.sort()
    lo = boot[int(0.025 * samples)]
    hi = boot[min(samples - 1, int(0.975 * samples))]
    return {"observed_difference": observed, "ci95_low": lo, "ci95_high": hi, "samples": samples}


def select_candidate(rows: Sequence[Dict[str, Any]], primary_metric: str = "MRR@10") -> Dict[str, Any]:
    if not rows:
        raise ValueError("no candidate rows")
    metric_order = [
        (primary_metric, True),
        ("NDCG@10", True),
        ("MRR@10", True),
        ("Recall@1", True),
        ("MeanRank", False),
        ("evaluation_seconds", False),
    ]

    def key(row: Dict[str, Any]):
        values = []
        for metric, higher in metric_order:
            value = float(row.get(metric, 0.0))
            values.append(value if higher else -value)
        return tuple(values)

    return max(rows, key=key)


def validate_model_dir(path: Path, expected_sha256: Optional[str] = None) -> str:
    if not path.is_dir():
        raise FileNotFoundError(f"candidate path does not exist: {path}")
    missing = [name for name in REQUIRED_MODEL_FILES if not (path / name).exists()]
    if missing:
        raise FileNotFoundError(f"{path} missing required files: {', '.join(missing)}")
    digest = sha256_file(path / "model.safetensors")
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(f"{path} model.safetensors sha256 mismatch: expected {expected_sha256}, got {digest}")
    return digest


def score_candidate(
    model_path: Path,
    pools: Sequence[CandidatePool],
    batch_size: int,
    max_length: int,
    device: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[float], float, float]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    start_load = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path), local_files_only=True)
    model.to(device)
    model.eval()
    load_seconds = time.perf_counter() - start_load

    ranks: List[int] = []
    rr_values: List[float] = []
    details: List[Dict[str, Any]] = []
    tie_queries = 0
    pairs: List[Tuple[str, str, str, str, int]] = []
    for pool_index, pool in enumerate(pools):
        for candidate_index, (doc_id, doc_text) in enumerate(pool.candidates):
            pairs.append((pool.query, doc_text, pool.query_id, doc_id, candidate_index))

    score_by_query: Dict[str, List[float]] = {pool.query_id: [] for pool in pools}
    start_eval = time.perf_counter()
    with torch.inference_mode():
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start:start + batch_size]
            encoded = tokenizer(
                [x[0] for x in batch],
                [x[1] for x in batch],
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            logits = model(**encoded).logits
            if logits.ndim == 1:
                logits = logits.unsqueeze(-1)
            if logits.shape[-1] < 1:
                raise RuntimeError(f"invalid logits shape: {tuple(logits.shape)}")
            scores = logits[:, 0].detach().cpu().float().tolist()
            if not all(math.isfinite(float(score)) for score in scores):
                raise RuntimeError("non-finite logits")
            for item, score in zip(batch, scores):
                score_by_query[item[2]].append(float(score))
    eval_seconds = time.perf_counter() - start_eval

    for pool in pools:
        scores = score_by_query[pool.query_id]
        if len(scores) != len(pool.candidates):
            raise RuntimeError(f"query {pool.query_id} has {len(scores)} scores for {len(pool.candidates)} candidates")
        rank, top_index = rank_positive(scores, pool.positive_index)
        ranks.append(rank)
        rr_values.append(1.0 / rank if rank <= 10 else 0.0)
        score_counts = {}
        for score in scores:
            score_counts[score] = score_counts.get(score, 0) + 1
        if any(count > 1 for count in score_counts.values()):
            tie_queries += 1
        negative_scores = [score for idx, score in enumerate(scores) if idx != pool.positive_index]
        details.append(
            {
                "query_id": pool.query_id,
                "positive_rank": rank,
                "reciprocal_rank": rr_values[-1],
                "ndcg_contribution": 1.0 / math.log2(rank + 1) if rank <= 10 else 0.0,
                "top_predicted_document_id": pool.candidates[top_index][0],
                "positive_document_id": pool.positive_id,
                "positive_score": scores[pool.positive_index],
                "highest_negative_score": max(negative_scores) if negative_scores else None,
                "score_margin": scores[pool.positive_index] - max(negative_scores) if negative_scores else None,
            }
        )

    metrics = compute_metrics(ranks, candidates_per_query=len(pools[0].candidates))
    metrics["TieScoreQueries"] = tie_queries
    metrics["load_seconds"] = load_seconds
    metrics["evaluation_seconds"] = eval_seconds
    metrics["queries_per_second"] = len(pools) / eval_seconds if eval_seconds else 0.0
    metrics["pairs_per_second"] = len(pairs) / eval_seconds if eval_seconds else 0.0

    del model
    del tokenizer
    gc.collect()
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.empty_cache()

    return metrics, details, rr_values, load_seconds, eval_seconds


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate local reranker candidates on a fixed split.")
    parser.add_argument("--dataset-jsonl", type=Path, required=True)
    parser.add_argument("--split", choices=["validation", "test"], default="validation")
    parser.add_argument("--candidate", action="append", type=Path, required=True)
    parser.add_argument("--candidate-name", action="append", default=[])
    parser.add_argument("--expected-sha256", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=Path("fine-tuning/reranking/results/candidate_evaluation"))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--num-negatives", type=int, default=31)
    parser.add_argument("--tfidf-top-k-pool", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--offline", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.offline:
        set_offline_env()
    if args.batch_size <= 0 or args.max_length <= 0:
        raise ValueError("batch size and max length must be positive")

    examples = deduplicate_pairs(load_jsonl_dataset(args.dataset_jsonl))
    if all(item.split in {"train", "validation", "test"} for item in examples):
        splits = {
            name: [item for item in examples if item.split == name]
            for name in ("train", "validation", "test")
        }
    else:
        splits = split_by_passage_group(examples, seed=args.seed)
    report = dataset_report(splits)
    assert_no_blocking_leakage(report)

    eval_examples = splits[args.split]
    if not eval_examples:
        raise RuntimeError(f"split {args.split} is empty")
    negatives = build_tfidf_negatives(
        eval_examples,
        num_negatives=args.num_negatives,
        top_k_pool=args.tfidf_top_k_pool,
        seed=args.seed + (23 if args.split == "validation" else 29),
    )
    pools = build_candidate_pools(eval_examples, negatives, seed=args.seed)
    pool_sizes = [len(pool.candidates) for pool in pools]

    expected = {}
    for raw in args.expected_sha256:
        name, digest = raw.split("=", 1)
        expected[name] = digest

    summaries = []
    per_candidate_rr = {}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for index, candidate_path in enumerate(args.candidate):
        name = args.candidate_name[index] if index < len(args.candidate_name) else candidate_path.name
        digest = validate_model_dir(candidate_path, expected.get(name) or DEFAULT_EXPECTED_HASHES.get(name))
        metrics, details, rr_values, _, _ = score_candidate(
            candidate_path,
            pools=pools,
            batch_size=args.batch_size,
            max_length=args.max_length,
            device=args.device,
        )
        row = {"candidate": name, "path": str(candidate_path), "sha256": digest, **metrics}
        summaries.append(row)
        per_candidate_rr[name] = rr_values
        write_jsonl(args.output_dir / f"{args.split}_{name}_per_query.jsonl", details)

    selection = select_candidate(summaries, primary_metric="MRR@10")
    bootstrap = {}
    if len(summaries) == 2:
        left, right = summaries[0]["candidate"], summaries[1]["candidate"]
        bootstrap[f"{left}_vs_{right}"] = paired_bootstrap(
            per_candidate_rr[left],
            per_candidate_rr[right],
            seed=args.seed,
            samples=args.bootstrap_samples,
        )

    payload = {
        "split": args.split,
        "dataset_jsonl": str(args.dataset_jsonl),
        "dataset_checksum": checksum_paths([args.dataset_jsonl]),
        "dataset_report": report,
        "candidate_pool": {
            "num_queries": len(pools),
            "min_size": min(pool_sizes),
            "max_size": max(pool_sizes),
            "mean_size": sum(pool_sizes) / len(pool_sizes),
            "num_negatives": args.num_negatives,
            "tfidf_top_k_pool": args.tfidf_top_k_pool,
            "seed": args.seed,
        },
        "metrics": summaries,
        "selection": selection,
        "bootstrap": bootstrap,
        "note": "Selection must use validation only. Run test only after the selected candidate is frozen.",
    }
    write_json(args.output_dir / f"{args.split}_summary.json", payload)
    write_csv(args.output_dir / f"{args.split}_metrics.csv", summaries)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
