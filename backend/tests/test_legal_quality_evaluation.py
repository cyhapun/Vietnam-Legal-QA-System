import json
from pathlib import Path

import pytest

from app.services.legal_quality_evaluation import (
    build_stage_trace,
    compute_quality_metrics,
    detect_unsupported_legal_references,
    extract_citation_ids,
    invalid_citation_ids,
    load_corpus_source_ids,
    load_quality_dataset,
    parse_quality_record,
    validate_dataset_sources,
)
from scripts.evaluate_legal_quality import _context_text_for_diagnostics
from scripts.audit_legal_corpus_integrity import audit_json_corpus


FIXTURE = Path(__file__).parent / "fixtures" / "legal_retrieval_quality.jsonl"


def test_quality_dataset_schema_and_sources_are_valid():
    records = load_quality_dataset(FIXTURE)
    corpus_source_ids = load_corpus_source_ids(Path(__file__).parents[1] / "data" / "processed")

    assert len(records) >= 20
    assert not validate_dataset_sources(records, corpus_source_ids)
    assert any("LDD_2024_D27_K3" in record.required_source_ids for record in records)
    assert any("LDD_2024_D45_K1" in record.required_source_ids for record in records)


def test_quality_record_requires_expected_sources():
    with pytest.raises(ValueError, match="At least one"):
        parse_quality_record({
            "id": "bad",
            "question": "question",
            "required_source_ids": [],
            "acceptable_source_ids": [],
            "critical": False,
            "category": "test",
            "question_type": "test",
        })


def test_metrics_calculate_hits_recall_mrr_and_critical_misses():
    records = [
        parse_quality_record({
            "id": "hit",
            "question": "q1",
            "required_source_ids": ["A"],
            "acceptable_source_ids": [],
            "critical": True,
            "category": "c",
            "question_type": "direct",
        }),
        parse_quality_record({
            "id": "miss",
            "question": "q2",
            "required_source_ids": ["Z"],
            "acceptable_source_ids": ["Y"],
            "critical": True,
            "category": "c",
            "question_type": "direct",
        }),
    ]
    traces = [
        build_stage_trace(records[0], ["B", "A"], ["A"], total_ms=100.0, ttft_ms=80.0),
        build_stage_trace(records[1], ["A", "B"], ["B"], total_ms=200.0, ttft_ms=160.0),
    ]

    metrics = compute_quality_metrics(records, traces)

    assert metrics["retrieval_hit_at_10"] == 0.5
    assert metrics["reranker_hit_at_5"] == 0.5
    assert metrics["mrr_at_10"] == 0.25
    assert metrics["critical_miss_count"] == 1
    assert metrics["median_total_ms"] == 150.0
    assert metrics["median_ttft_ms"] == 120.0


def test_acceptable_sources_count_as_relevant():
    record = parse_quality_record({
        "id": "acceptable",
        "question": "q",
        "required_source_ids": ["A"],
        "acceptable_source_ids": ["B"],
        "critical": False,
        "category": "c",
        "question_type": "direct",
    })

    trace = build_stage_trace(record, ["B"], ["B"])

    assert trace.retrieval_rank == 1
    assert trace.final_context_presence is True
    assert trace.failure_stage == "passed"


def test_citation_validation_extracts_and_flags_invalid_ids():
    answer = 'Theo căn cứ <cite id="LDD_2024_D27_K3"> và LDD_2024_D45_K1.'

    citation_ids = extract_citation_ids(answer)

    assert citation_ids == ["LDD_2024_D27_K3"]
    assert invalid_citation_ids(["A", "B", "A"], ["A"]) == ["B"]


def test_unsupported_legal_reference_detection_is_conservative():
    answer = "Theo Điều 45 Luật Đất đai, người sử dụng đất phải có giấy chứng nhận."
    context = "Nguồn: Luật Đất đai 2024 | Điều 45 | Nội dung..."

    assert detect_unsupported_legal_references(answer, context) == []
    assert detect_unsupported_legal_references("Theo Điều 99 thì được miễn.", context) == ["Điều 99"]


def test_answer_diagnostic_context_includes_source_metadata():
    context = _context_text_for_diagnostics([
        {
            "content": "Nội dung điều khoản.",
            "metadata": {
                "source": "Luật Đất đai 2024",
                "dieu": 45,
                "khoan": 1,
            },
        }
    ])

    assert "Luật Đất đai 2024" in context
    assert "Điều 45" in context
    assert "Khoản 1" in context
    assert detect_unsupported_legal_references(
        "Theo Luật Đất đai 2024 Điều 45 Khoản 1 thì được áp dụng.",
        context,
    ) == []
    assert detect_unsupported_legal_references("Theo Điều 99 thì được áp dụng.", context) == ["Điều 99"]


def test_generated_report_helpers_do_not_require_answer_content():
    record = parse_quality_record({
        "id": "trace",
        "question": "q",
        "required_source_ids": ["A"],
        "acceptable_source_ids": [],
        "critical": False,
        "category": "c",
        "question_type": "direct",
    })

    trace = build_stage_trace(record, ["C"], ["C"], citation_ids=["X"])

    assert trace.failure_stage == "missing_from_qdrant_top10"
    assert trace.invalid_citation_ids == ("X",)


def test_corpus_integrity_audit_is_read_only(tmp_path):
    corpus_dir = tmp_path / "processed"
    corpus_dir.mkdir()
    (corpus_dir / "law.json").write_text(
        json.dumps({
            "law_info": {"law_id": "LAW_2024", "law_name": "Luật thử nghiệm"},
            "clauses": [
                {
                    "id": "LAW_2024_D1_K1",
                    "position": {"article": 1, "clause": 1},
                    "content": "Nội dung.",
                },
                {
                    "id": "LAW_2024_D2",
                    "position": {},
                    "content": "",
                },
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    report = audit_json_corpus(corpus_dir)

    assert report["json_clause_count"] == 2
    assert report["empty_text_ids"] == ["LAW_2024_D2"]
    assert report["malformed_metadata_ids"] == ["LAW_2024_D2"]
