import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "backend" / "scripts" / "migrate_embedding_index.py"
spec = importlib.util.spec_from_file_location("migrate_embedding_index", SCRIPT_PATH)
migration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = migration
spec.loader.exec_module(migration)


class _Vector:
    def __init__(self, size):
        self.size = size


class _Params:
    def __init__(self, vectors, sparse_vectors=None):
        self.vectors = vectors
        self.sparse_vectors = sparse_vectors or {}


class _Config:
    def __init__(self, vectors, sparse_vectors=None):
        self.params = _Params(vectors, sparse_vectors)


class _CollectionInfo:
    def __init__(self, vectors, sparse_vectors=None, points_count=0):
        self.config = _Config(vectors, sparse_vectors)
        self.points_count = points_count


class _FakeClient:
    def __init__(self, collections):
        self.collections = collections
        self.created = []
        self.deleted = []

    def get_collection(self, name):
        if name not in self.collections:
            raise RuntimeError("missing")
        return self.collections[name]

    def create_collection(self, collection_name, **kwargs):
        self.created.append((collection_name, kwargs))

    def delete_collection(self, collection_name):
        self.deleted.append(collection_name)


def _valid_info():
    return _CollectionInfo(
        {
            "": _Vector(1),
            "text-dense": _Vector(1024),
        },
        {"text-sparse": object()},
    )


def test_versioned_name_generation():
    assert migration.target_name_with_version("vietlaw_clauses_bge_m3_ft_v1", 1) == "vietlaw_clauses_bge_m3_ft_v1"
    assert migration.target_name_with_version("vietlaw_clauses_bge_m3_ft_v1", 2) == "vietlaw_clauses_bge_m3_ft_v2"
    assert migration.target_name_with_version("vietlaw_clauses_bge_m3_ft_v2", 1) == "vietlaw_clauses_bge_m3_ft_v2"
    assert migration.target_name_with_version("vietlaw_clauses_bge_m3_ft_v2", 3) == "vietlaw_clauses_bge_m3_ft_v3"
    assert migration.target_name_with_version("custom_collection", 3) == "custom_collection_v3"


def test_resolve_target_uses_existing_compatible_collection():
    client = _FakeClient({"vietlaw_clauses_bge_m3_ft_v1": _valid_info()})

    name, exists, reason = migration.resolve_target_collection(client, "vietlaw_clauses_bge_m3_ft_v1", 1024)

    assert name == "vietlaw_clauses_bge_m3_ft_v1"
    assert exists is True
    assert reason == "existing_compatible"
    assert client.deleted == []


def test_resolve_target_skips_existing_incompatible_collection():
    client = _FakeClient(
        {
            "vietlaw_clauses_bge_m3_ft_v1": _CollectionInfo(
                {"": _Vector(1), "text-dense": _Vector(768)},
                {"text-sparse": object()},
            )
        }
    )

    name, exists, reason = migration.resolve_target_collection(client, "vietlaw_clauses_bge_m3_ft_v1", 1024)

    assert name == "vietlaw_clauses_bge_m3_ft_v2"
    assert exists is False
    assert reason == "missing"
    assert client.deleted == []


def test_finite_dimension_validation_rejects_bad_vectors():
    with pytest.raises(ValueError, match="dimension mismatch"):
        migration.ensure_finite_dimension([0.1], 2, "clause-1")

    with pytest.raises(ValueError, match="NaN or Inf"):
        migration.ensure_finite_dimension([0.1, float("nan")], 2, "clause-1")


def test_build_qdrant_point_is_deterministic():
    record = migration.ClauseRecord(
        clause_id="LDD_2024_D1_K1",
        law_id="LDD_2024",
        law_name="Luật Đất đai",
        category="land",
        content="Nội dung điều khoản",
        position={"article": "1"},
        cross_references=[],
    )

    point_a = migration.build_qdrant_point(record, [0.1, 0.2], {"indices": [1], "values": [0.5]})
    point_b = migration.build_qdrant_point(record, [0.1, 0.2], {"indices": [1], "values": [0.5]})

    assert point_a.id == point_b.id
    assert point_a.payload["id"] == "LDD_2024_D1_K1"
    assert "text-dense" in point_a.vector
    assert "" in point_a.vector
    assert "text-sparse" in point_a.vector


def test_grouped_law_records_groups_clauses_by_law():
    records = [
        migration.ClauseRecord("c1", "L1", "Law 1", "all", "a", {}, []),
        migration.ClauseRecord("c2", "L1", "Law 1", "all", "b", {}, []),
        migration.ClauseRecord("c3", "L2", "Law 2", "land", "c", {}, []),
    ]

    grouped = migration.grouped_law_records(records)

    assert [law["law_id"] for law in grouped] == ["L1", "L2"]
    assert [len(law["clauses"]) for law in grouped] == [2, 1]


def test_dry_run_reports_counts_without_qdrant(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "law.json").write_text(
        json.dumps(
            {
                "law_info": {"law_id": "LDD_2024", "law_name": "Luật Đất đai"},
                "clauses": [
                    {"id": "c1", "content": "a"},
                    {"id": "c2", "content": "b"},
                ],
            }
        ),
        encoding="utf-8",
    )
    embedding_dir = tmp_path / "embedding"
    embedding_dir.mkdir()
    (embedding_dir / "model.safetensors").write_bytes(b"weights")

    args = migration.parse_args(
        [
            "--dry-run",
            "--source-corpus",
            str(corpus),
            "--embedding-model",
            str(embedding_dir),
            "--batch-size",
            "1",
            "--max-seq-length",
            "512",
        ]
    )

    report = migration.run_dry_run(args)

    assert report["status"] == "dry_run"
    assert report["expected_points"] == 2
    assert report["estimated_batches"] == 2
    assert report["max_seq_length"] == 512
    assert report["will_mutate"] is False


def test_create_collection_never_deletes_existing_collection(monkeypatch):
    fake_models = type(
        "FakeModels",
        (),
        {
            "Distance": type("Distance", (), {"COSINE": "Cosine"}),
            "VectorParams": lambda **kwargs: kwargs,
            "SparseVectorParams": lambda: {"sparse": True},
        },
    )
    monkeypatch.setitem(sys.modules, "qdrant_client.http.models", fake_models)

    client = _FakeClient({})
    migration.create_collection(client, "new_collection", 1024)

    assert client.created
    assert client.deleted == []
