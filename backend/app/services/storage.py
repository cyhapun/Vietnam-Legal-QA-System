"""
Storage bootstrap for Qdrant + PostgreSQL-backed legal corpus persistence.

This module provides an initial abstraction for the new storage backend while
preserving backward compatibility with the existing FAISS-based flow.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.config import (
    POSTGRES_DSN,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_URL,
    STORAGE_BACKEND,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.storage")


class StorageInitializationError(RuntimeError):
    """Raised when the database-backed storage layer cannot be initialized."""


def _is_db_backend_enabled() -> bool:
    return STORAGE_BACKEND.lower() in {"qdrant_postgres", "postgres", "postgresql", "qdrant"}


def initialize_storage() -> Dict[str, Any]:
    """Initialize PostgreSQL schema and Qdrant collection if the DB backend is enabled."""
    if not _is_db_backend_enabled():
        logger.info("Storage backend %s requested; skipping DB initialization.", STORAGE_BACKEND)
        return {"backend": STORAGE_BACKEND, "postgres": "skipped", "qdrant": "skipped"}

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "psycopg is required for database-backed storage. Install backend requirements first."
        ) from exc

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qdrant_models
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "qdrant-client is required for vector storage. Install backend requirements first."
        ) from exc

    schema_sql = """
    CREATE TABLE IF NOT EXISTS laws (
        law_id TEXT PRIMARY KEY,
        law_name TEXT NOT NULL,
        summary TEXT,
        category TEXT,
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS clauses (
        id TEXT PRIMARY KEY,
        law_id TEXT NOT NULL REFERENCES laws(law_id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        position JSONB DEFAULT '{}'::jsonb,
        cross_references JSONB DEFAULT '[]'::jsonb,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS indexing_runs (
        id SERIAL PRIMARY KEY,
        source TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        started_at TIMESTAMPTZ DEFAULT NOW(),
        finished_at TIMESTAMPTZ,
        details JSONB DEFAULT '{}'::jsonb
    );
    """

    with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(schema_sql)

    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    qdrant_client.recreate_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=qdrant_models.VectorParams(size=1024, distance=qdrant_models.Distance.COSINE),
    )

    logger.info("Database-backed storage initialized: postgres=%s qdrant=%s", POSTGRES_DSN, QDRANT_COLLECTION)
    return {
        "backend": STORAGE_BACKEND,
        "postgres": "ready",
        "qdrant_collection": QDRANT_COLLECTION,
    }


def ingest_documents(records: List[Dict[str, Any]]) -> int:
    """Persist legal document records into PostgreSQL and upsert vectors into Qdrant."""
    if not records:
        return 0

    if not _is_db_backend_enabled():
        logger.info("Skipping ingestion because storage backend %s is not database-backed.", STORAGE_BACKEND)
        return 0

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "psycopg is required for database-backed storage. Install backend requirements first."
        ) from exc

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qdrant_models
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "qdrant-client is required for vector storage. Install backend requirements first."
        ) from exc

    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)

    with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for record in records:
                law_id = record["law_id"]
                law_name = record.get("law_name", "")
                summary = record.get("summary", "")
                category = record.get("category", "all")
                metadata = record.get("metadata", {})

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
                    (law_id, law_name, summary, category, json.dumps(metadata)),
                )

                for clause in record.get("clauses", []):
                    clause_id = clause["id"]
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
                            clause_id,
                            law_id,
                            clause.get("content", ""),
                            json.dumps(clause.get("position", {})),
                            json.dumps(clause.get("cross_references", [])),
                        ),
                    )

                    embedding = clause.get("embedding")
                    if embedding:
                        qdrant_client.upsert(
                            collection_name=QDRANT_COLLECTION,
                            points=[
                                qdrant_models.PointStruct(
                                    id=clause_id,
                                    vector=embedding,
                                    payload={
                                        "law_id": law_id,
                                        "content": clause.get("content", ""),
                                        "category": category,
                                    },
                                )
                            ],
                        )

    logger.info("Ingested %d document record(s) into database-backed storage.", len(records))
    return len(records)
