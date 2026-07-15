import importlib.util
import math
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "fine-tuning" / "reranking" / "evaluate_candidates.py"
spec = importlib.util.spec_from_file_location("reranker_candidate_eval", SCRIPT_PATH)
eval_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = eval_mod
spec.loader.exec_module(eval_mod)


def _example(query_id, query, positive_id, positive, split="validation"):
    return eval_mod.Example(
        query_id=query_id,
        query=query,
        positive_id=positive_id,
        positive=positive,
        split=split,
    )


def test_mrr_ndcg_recall_and_mean_rank():
    metrics = eval_mod.compute_metrics([1, 2, 11], candidates_per_query=32)

    assert metrics["MRR@10"] == pytest.approx((1.0 + 0.5 + 0.0) / 3)
    assert metrics["NDCG@10"] == pytest.approx((1.0 + 1.0 / math.log2(3) + 0.0) / 3)
    assert metrics["Recall@1"] == pytest.approx(1 / 3)
    assert metrics["Recall@3"] == pytest.approx(2 / 3)
    assert metrics["Recall@10"] == pytest.approx(2 / 3)
    assert metrics["MeanRank"] == pytest.approx(14 / 3)
    assert metrics["PositiveMissingTop10"] == 1


def test_stable_sort_tie_keeps_lower_original_index():
    rank, top_index = eval_mod.rank_positive([0.8, 0.8, 0.1], positive_index=1)

    assert top_index == 0
    assert rank == 2


def test_missing_positive_index_raises():
    with pytest.raises(ValueError, match="positive_index"):
        eval_mod.rank_positive([0.1], positive_index=5)


def test_candidate_pool_consistency_and_positive_index():
    examples = [
        _example("q1", "query one", "p1", "positive one"),
        _example("q2", "query two", "p2", "positive two"),
    ]
    negatives = [[examples[1]], [examples[0]]]

    pools_a = eval_mod.build_candidate_pools(examples, negatives, seed=42)
    pools_b = eval_mod.build_candidate_pools(examples, negatives, seed=42)

    assert pools_a == pools_b
    assert all(pool.candidates[pool.positive_index][0] == pool.positive_id for pool in pools_a)
    assert all(len(pool.candidates) == 2 for pool in pools_a)


def test_dataset_leakage_detector_blocks_positive_overlap():
    splits = {
        "train": [_example("q1", "query one", "p1", "same positive", "train")],
        "validation": [_example("q2", "query two", "p1", "same positive", "validation")],
        "test": [_example("q3", "query three", "p3", "third positive", "test")],
    }

    report = eval_mod.dataset_report(splits)

    with pytest.raises(RuntimeError, match="Positive document leakage"):
        eval_mod.assert_no_blocking_leakage(report)


def test_model_selection_uses_metric_order():
    rows = [
        {"candidate": "a", "MRR@10": 0.9, "NDCG@10": 0.99, "Recall@1": 0.9, "MeanRank": 1.2, "evaluation_seconds": 5},
        {"candidate": "b", "MRR@10": 0.91, "NDCG@10": 0.8, "Recall@1": 0.8, "MeanRank": 1.5, "evaluation_seconds": 4},
    ]

    selected = eval_mod.select_candidate(rows, primary_metric="MRR@10")

    assert selected["candidate"] == "b"


def test_model_selection_tie_breaks_on_ndcg():
    rows = [
        {"candidate": "a", "MRR@10": 0.9, "NDCG@10": 0.8, "Recall@1": 0.9, "MeanRank": 1.2, "evaluation_seconds": 4},
        {"candidate": "b", "MRR@10": 0.9, "NDCG@10": 0.81, "Recall@1": 0.8, "MeanRank": 1.5, "evaluation_seconds": 5},
    ]

    selected = eval_mod.select_candidate(rows, primary_metric="MRR@10")

    assert selected["candidate"] == "b"


def test_bootstrap_is_deterministic():
    left = [1.0, 0.5, 0.0, 1.0]
    right = [1.0, 1.0, 0.0, 0.5]

    first = eval_mod.paired_bootstrap(left, right, seed=7, samples=1000)
    second = eval_mod.paired_bootstrap(left, right, seed=7, samples=1000)

    assert first == second
    assert first["samples"] == 1000


def test_split_by_passage_group_removes_positive_text_overlap():
    examples = [
        _example("q1", "q1", "p1", "shared positive", ""),
        _example("q2", "q2", "p1", "shared positive", ""),
        _example("q3", "q3", "p2", "other positive", ""),
        _example("q4", "q4", "p3", "third positive", ""),
    ]

    splits = eval_mod.split_by_passage_group(examples, seed=42)
    locations = {}
    for split, items in splits.items():
        for item in items:
            locations.setdefault(item.positive, set()).add(split)

    assert all(len(split_names) == 1 for split_names in locations.values())
