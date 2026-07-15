#!/usr/bin/env python3
"""Build a versioned Qdrant collection with the configured local embedding model."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.knowledge_base import determine_category  # noqa: E402


DENSE_VECTOR_NAME = "text-dense"
SPARSE_VECTOR_NAME = "text-sparse"
DUMMY_VECTOR_NAME = ""
DEFAULT_TARGET_COLLECTION = "vietlaw_clauses_bge_m3_ft_v1"
DEFAULT_CACHE_COLLECTION = "semantic_cache_bge_m3_ft_v1"


@dataclass(frozen=True)
class ClauseRecord:
    clause_id: str
    law_id: str
    law_name: str
    category: str
    content: str
    position: Dict[str, Any]
    cross_references: List[Any]


def set_offline_env() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_DIR.resolve()))
    except ValueError:
        return str(path)


def corpus_inventory(source_corpus: Path) -> Dict[str, Any]:
    files = sorted(source_corpus.glob("*.json"))
    inventory = []
    total_clauses = 0
    combined = hashlib.sha256()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        clause_count = len(data.get("clauses") or [])
        file_hash = sha256_file(path)
        total_clauses += clause_count
        inventory.append(
            {
                "path": repo_relative(path),
                "size_bytes": path.stat().st_size,
                "sha256": file_hash,
                "clause_count": clause_count,
            }
        )
        combined.update(repo_relative(path).encode("utf-8"))
        combined.update(b"\0")
        combined.update(file_hash.encode("ascii"))
        combined.update(b"\0")

    return {
        "source_corpus": repo_relative(source_corpus),
        "file_count": len(files),
        "clause_count": total_clauses,
        "files": inventory,
        "combined_sha256": combined.hexdigest(),
    }


def load_clause_records(source_corpus: Path) -> List[ClauseRecord]:
    records: List[ClauseRecord] = []
    for path in sorted(source_corpus.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        law_info = data.get("law_info") or {}
        law_id = str(law_info.get("law_id") or "").strip()
        law_name = str(law_info.get("law_name") or "").strip()
        category = determine_category(law_name)
        for clause in data.get("clauses") or []:
            clause_id = str(clause.get("id") or "").strip()
            content = str(clause.get("content") or "").strip()
            if not clause_id or not content:
                continue
            records.append(
                ClauseRecord(
                    clause_id=clause_id,
                    law_id=law_id,
                    law_name=law_name,
                    category=category,
                    content=content,
                    position=clause.get("position") or {},
                    cross_references=clause.get("cross_references") or [],
                )
            )
    return records


def grouped_law_records(records: Sequence[ClauseRecord]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for record in records:
        law = grouped.setdefault(
            record.law_id,
            {
                "law_id": record.law_id,
                "law_name": record.law_name,
                "summary": "",
                "category": record.category,
                "metadata": {"law_name": record.law_name},
                "clauses": [],
            },
        )
        law["clauses"].append(record)
    return list(grouped.values())


def upsert_postgres_metadata(records: Sequence[ClauseRecord], postgres_dsn: str) -> Dict[str, int]:
    """Idempotently upsert law/clause metadata without touching Qdrant."""
    import psycopg

    from app.services.storage import _ensure_schema

    _ensure_schema()
    laws = grouped_law_records(records)
    law_count = 0
    clause_count = 0
    with psycopg.connect(postgres_dsn, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for law in laws:
                cursor.execute(
                    """
                    INSERT INTO laws (law_id, law_name, summary, category, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (law_id) DO UPDATE SET
                        law_name = EXCLUDED.law_name,
                        summary = EXCLUDED.summary,
                        category = EXCLUDED.category,
                        metadata = EXCLUDED.metadata
                    """,
                    (
                        law["law_id"],
                        law["law_name"],
                        law["summary"],
                        law["category"],
                        json.dumps(law["metadata"]),
                    ),
                )
                law_count += 1
                for clause in law["clauses"]:
                    cursor.execute(
                        """
                        INSERT INTO clauses (id, law_id, content, position, cross_references)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            law_id = EXCLUDED.law_id,
                            content = EXCLUDED.content,
                            position = EXCLUDED.position,
                            cross_references = EXCLUDED.cross_references
                        """,
                        (
                            clause.clause_id,
                            clause.law_id,
                            clause.content,
                            json.dumps(clause.position),
                            json.dumps(clause.cross_references),
                        ),
                    )
                    clause_count += 1
    return {"laws": law_count, "clauses": clause_count}


def deterministic_point_id(clause_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, clause_id))


def ensure_finite_dimension(vector: Sequence[float], expected_dimension: int, clause_id: str) -> None:
    if len(vector) != expected_dimension:
        raise ValueError(
            f"Embedding dimension mismatch for {clause_id}: expected {expected_dimension}, got {len(vector)}."
        )
    if not all(math.isfinite(float(value)) for value in vector):
        raise ValueError(f"Embedding contains NaN or Inf for {clause_id}.")


def build_qdrant_point(record: ClauseRecord, dense_vector: Sequence[float], sparse_vector: Optional[Dict[str, Any]]):
    from qdrant_client.http import models as qdrant_models

    vector: Dict[str, Any] = {
        DUMMY_VECTOR_NAME: [0.0],
        DENSE_VECTOR_NAME: list(dense_vector),
    }
    if sparse_vector and sparse_vector.get("indices"):
        vector[SPARSE_VECTOR_NAME] = qdrant_models.SparseVector(
            indices=sparse_vector["indices"],
            values=sparse_vector["values"],
        )

    return qdrant_models.PointStruct(
        id=deterministic_point_id(record.clause_id),
        vector=vector,
        payload={
            "id": record.clause_id,
            "law_id": record.law_id,
            "law_name": record.law_name,
            "content": record.content,
            "category": record.category,
            "position": record.position,
            "cross_references": record.cross_references,
        },
    )


def target_name_with_version(base_name: str, version: int) -> str:
    match = re.search(r"_v\d+$", base_name)
    if version == 1 and match:
        return base_name
    if match:
        return f"{base_name[:match.start()]}_v{version}"
    return f"{base_name}_v{version}"


def _collection_exists(client, collection_name: str) -> bool:
    try:
        client.get_collection(collection_name)
        return True
    except Exception:
        return False


def _named_vector_size(collection_info, vector_name: str) -> Optional[int]:
    vectors = collection_info.config.params.vectors
    if isinstance(vectors, dict):
        vector_config = vectors.get(vector_name)
        return getattr(vector_config, "size", None) if vector_config is not None else None
    if vector_name == DUMMY_VECTOR_NAME:
        return getattr(vectors, "size", None)
    return None


def collection_schema_matches(collection_info, expected_dimension: int) -> bool:
    sparse_vectors = getattr(collection_info.config.params, "sparse_vectors", None)
    return (
        _named_vector_size(collection_info, DUMMY_VECTOR_NAME) == 1
        and _named_vector_size(collection_info, DENSE_VECTOR_NAME) == expected_dimension
        and bool(sparse_vectors)
        and SPARSE_VECTOR_NAME in sparse_vectors
    )


def resolve_target_collection(client, preferred_name: str, expected_dimension: int) -> Tuple[str, bool, str]:
    for version in range(1, 100):
        candidate = target_name_with_version(preferred_name, version)
        try:
            info = client.get_collection(candidate)
        except Exception:
            return candidate, False, "missing"
        if collection_schema_matches(info, expected_dimension):
            return candidate, True, "existing_compatible"
    raise RuntimeError(f"Could not find an available versioned collection name for {preferred_name}.")


def create_collection(client, collection_name: str, dimension: int) -> None:
    from qdrant_client.http import models as qdrant_models

    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            DUMMY_VECTOR_NAME: qdrant_models.VectorParams(size=1, distance=qdrant_models.Distance.COSINE),
            DENSE_VECTOR_NAME: qdrant_models.VectorParams(size=dimension, distance=qdrant_models.Distance.COSINE),
        },
        sparse_vectors_config={SPARSE_VECTOR_NAME: qdrant_models.SparseVectorParams()},
    )


def create_semantic_cache_collection(client, collection_name: str, dimension: int) -> str:
    if _collection_exists(client, collection_name):
        info = client.get_collection(collection_name)
        if _named_vector_size(info, DUMMY_VECTOR_NAME) != dimension:
            raise RuntimeError(
                f"Semantic cache collection '{collection_name}' dimension mismatch; expected {dimension}."
            )
        return "existing"

    from qdrant_client.http import models as qdrant_models

    client.create_collection(
        collection_name=collection_name,
        vectors_config=qdrant_models.VectorParams(size=dimension, distance=qdrant_models.Distance.COSINE),
    )
    return "created"


def batch_items(items: Sequence[Any], batch_size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def existing_point_ids(client, collection_name: str, point_ids: Sequence[str]) -> set[str]:
    if not point_ids:
        return set()
    try:
        points = client.retrieve(collection_name=collection_name, ids=list(point_ids), with_payload=False)
    except Exception:
        return set()
    return {str(point.id) for point in points}


def write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def build_base_report(args: argparse.Namespace, inventory: Dict[str, Any], target_exists: Optional[bool]) -> Dict[str, Any]:
    embedding_path = Path(args.embedding_model)
    weight_path = embedding_path / "model.safetensors"
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_corpus": inventory,
        "embedding_path": args.embedding_model,
        "embedding_weight_sha256": sha256_file(weight_path) if weight_path.exists() else None,
        "embedding_dimension": args.embedding_dimension,
        "target_collection_requested": args.target_collection,
        "semantic_cache_collection": args.semantic_cache_collection,
        "schema": {
            "dense_vector": DENSE_VECTOR_NAME,
            "dense_dimension": args.embedding_dimension,
            "dense_distance": "Cosine",
            "sparse_vector": SPARSE_VECTOR_NAME,
            "dummy_vector": DUMMY_VECTOR_NAME,
            "dummy_dimension": 1,
        },
        "batch_size": args.batch_size,
        "max_seq_length": args.max_seq_length,
        "device": args.device,
        "resume": args.resume,
        "dry_run": args.dry_run,
        "target_exists": target_exists,
    }


def run_dry_run(args: argparse.Namespace) -> Dict[str, Any]:
    inventory = corpus_inventory(Path(args.source_corpus))
    report = build_base_report(args, inventory, target_exists=None)
    report.update(
        {
            "status": "dry_run",
            "expected_points": inventory["clause_count"],
            "estimated_batches": math.ceil(inventory["clause_count"] / args.batch_size),
            "will_mutate": False,
        }
    )
    return report


def run_migration(args: argparse.Namespace) -> Dict[str, Any]:
    set_offline_env()
    start = time.perf_counter()
    source_corpus = Path(args.source_corpus)
    inventory = corpus_inventory(source_corpus)
    records = load_clause_records(source_corpus)

    from qdrant_client import QdrantClient
    from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
    from app.services.sparse_vector import SparseVectorGenerator

    client = QdrantClient(url=args.qdrant_url, api_key=args.qdrant_api_key or None)
    postgres_counts = upsert_postgres_metadata(records, args.postgres_dsn)
    target_collection, target_exists, target_status = resolve_target_collection(
        client,
        args.target_collection,
        args.embedding_dimension,
    )
    if not target_exists:
        create_collection(client, target_collection, args.embedding_dimension)
    cache_status = create_semantic_cache_collection(
        client,
        args.semantic_cache_collection,
        args.embedding_dimension,
    )

    before_count = client.get_collection(target_collection).points_count or 0
    embedding = HuggingFaceEndpointEmbedding(
        model=args.embedding_model,
        mode="local",
        device=args.device,
        batch_size=args.batch_size,
        expected_dimension=args.embedding_dimension,
        local_files_only=True,
    )
    if args.max_seq_length is not None:
        local_engine = embedding._get_local_engine()
        if not hasattr(local_engine, "max_seq_length"):
            raise RuntimeError("Local embedding engine does not expose max_seq_length.")
        local_engine.max_seq_length = args.max_seq_length
    sparse_generator = SparseVectorGenerator()

    indexed = 0
    skipped = 0
    failed = 0
    errors: List[Dict[str, str]] = []

    for batch in batch_items(records, args.batch_size):
        point_ids = [deterministic_point_id(record.clause_id) for record in batch]
        existing = existing_point_ids(client, target_collection, point_ids) if args.resume else set()
        active_records = [record for record, point_id in zip(batch, point_ids) if point_id not in existing]
        skipped += len(batch) - len(active_records)
        if not active_records:
            continue

        try:
            vectors = embedding.embed_documents([record.content for record in active_records])
            points = []
            for record, vector in zip(active_records, vectors):
                ensure_finite_dimension(vector, args.embedding_dimension, record.clause_id)
                sparse_vector = sparse_generator.generate_sparse_vector(record.content)
                points.append(build_qdrant_point(record, vector, sparse_vector))
            client.upsert(collection_name=target_collection, points=points)
            indexed += len(points)
        except Exception as exc:
            failed += len(active_records)
            errors.append({"batch_start_clause_id": active_records[0].clause_id, "error": str(exc)})
            if len(errors) >= args.max_errors:
                break

    gc.collect()
    after_info = client.get_collection(target_collection)
    report = build_base_report(args, inventory, target_exists=target_exists)
    report.update(
        {
            "status": "completed" if failed == 0 else "failed",
            "target_collection": target_collection,
            "target_collection_status": target_status,
            "semantic_cache_status": cache_status,
            "expected_points": len(records),
            "postgres_upserted": postgres_counts,
            "point_count_before": before_count,
            "point_count_after": after_info.points_count,
            "indexed_points": indexed,
            "skipped_points": skipped,
            "failed_points": failed,
            "errors": errors,
            "elapsed_seconds": round(time.perf_counter() - start, 3),
        }
    )
    return report


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-corpus", default=str(BACKEND_DIR / "data" / "processed"))
    parser.add_argument("--target-collection", default=DEFAULT_TARGET_COLLECTION)
    parser.add_argument("--semantic-cache-collection", default=DEFAULT_CACHE_COLLECTION)
    parser.add_argument("--embedding-model", required=True)
    parser.add_argument("--embedding-dimension", type=positive_int, default=1024)
    parser.add_argument("--batch-size", type=positive_int, default=32)
    parser.add_argument("--max-seq-length", type=positive_int, default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://localhost:6333"))
    parser.add_argument("--qdrant-api-key", default=os.getenv("QDRANT_API_KEY", ""))
    parser.add_argument("--postgres-dsn", default=os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/vietlaw"))
    parser.add_argument("--report-path", default=str(REPO_DIR / "reports" / "index_migrations" / "migration_report.json"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-errors", type=positive_int, default=1)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        report = run_dry_run(args) if args.dry_run else run_migration(args)
        write_report(Path(args.report_path), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report.get("status") in {"dry_run", "completed"} else 1
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
