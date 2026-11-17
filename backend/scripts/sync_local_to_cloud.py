"""
Script đồng bộ dữ liệu từ PostgreSQL & Qdrant local lên Supabase & Qdrant Cloud.
Chạy:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/sync_local_to_cloud.py
"""
import sys
import os
import json
import psycopg
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.config import (
    POSTGRES_DSN,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
)

LOCAL_PG_DSN = "postgresql://postgres:postgres@localhost:15432/vietlaw"
LOCAL_QDRANT_URL = "http://localhost:6333"

def sync_postgres():
    print("\n[1/2] 🚀 Đang đồng bộ dữ liệu PostgreSQL từ Local lên Supabase...")
    with psycopg.connect(LOCAL_PG_DSN) as local_conn, psycopg.connect(POSTGRES_DSN) as cloud_conn:
        with local_conn.cursor() as loc_cur, cloud_conn.cursor() as cloud_cur:
            # 1. Sync laws
            loc_cur.execute("SELECT law_id, law_name, summary, category, metadata FROM laws")
            laws = loc_cur.fetchall()
            print(f"  • Đang đồng bộ {len(laws)} văn bản luật vào Supabase...")
            for law in laws:
                cloud_cur.execute(
                    """
                    INSERT INTO laws (law_id, law_name, summary, category, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (law_id) DO UPDATE SET
                        law_name = EXCLUDED.law_name,
                        summary = EXCLUDED.summary,
                        category = EXCLUDED.category,
                        metadata = EXCLUDED.metadata;
                    """,
                    (law[0], law[1], law[2], law[3], json.dumps(law[4]) if isinstance(law[4], dict) else law[4]),
                )
            cloud_conn.commit()
            print(f"  ✅ Đã đồng bộ thành công {len(laws)} văn bản luật!")

            # 2. Sync clauses
            loc_cur.execute("SELECT id, law_id, content, position, cross_references FROM clauses")
            clauses = loc_cur.fetchall()
            total_clauses = len(clauses)
            print(f"  • Đang đồng bộ {total_clauses} điều khoản vào Supabase theo lô...")
            params = [
                (
                    c[0],
                    c[1],
                    c[2],
                    json.dumps(c[3]) if isinstance(c[3], (dict, list)) else c[3],
                    json.dumps(c[4]) if isinstance(c[4], (dict, list)) else c[4],
                )
                for c in clauses
            ]
            batch_size = 500
            for i in range(0, total_clauses, batch_size):
                batch_params = params[i:i + batch_size]
                cloud_cur.executemany(
                    """
                    INSERT INTO clauses (id, law_id, content, position, cross_references)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    batch_params,
                )
                cloud_conn.commit()
                print(f"    - Tiến độ: {min(i + batch_size, total_clauses)}/{total_clauses} điều khoản...")
            print(f"  ✅ Đã đồng bộ hoàn tất toàn bộ {total_clauses} điều khoản lên Supabase!")

def sync_qdrant():
    print("\n[2/2] 🚀 Đang đồng bộ Vector Points từ Qdrant Local lên Qdrant Cloud...")
    local_client = QdrantClient(url=LOCAL_QDRANT_URL, timeout=30)
    cloud_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)

    # Lấy thông tin local
    local_info = local_client.get_collection(QDRANT_COLLECTION)
    total_local_points = local_info.points_count
    print(f"  • Tổng số vector trên Qdrant local: {total_local_points}")

    offset = None
    batch_size = 250
    synced = 0

    while True:
        records, next_offset = local_client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=batch_size,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )
        if not records:
            break

        # Convert records to PointStruct for upsert
        points_to_upload = [
            qdrant_models.PointStruct(
                id=r.id,
                vector=r.vector,
                payload=r.payload,
            )
            for r in records
        ]

        cloud_client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=points_to_upload,
            wait=True,
        )

        synced += len(points_to_upload)
        print(f"    - Đã tải lên Qdrant Cloud: {synced}/{total_local_points} vectors...")

        if next_offset is None:
            break
        offset = next_offset

    cloud_info = cloud_client.get_collection(QDRANT_COLLECTION)
    print(f"  ✅ Đồng bộ hoàn tất! Số vector trên Qdrant Cloud: {cloud_info.points_count}")

def main():
    print("=" * 65)
    print("  ĐỒNG BỘ DỮ LIỆU LOCAL LÊN CLOUD (SUPABASE & QDRANT)")
    print("=" * 65)
    sync_postgres()
    sync_qdrant()
    print("\n🎉 HOÀN TẤT ĐỒNG BỘ 100%! Cả Supabase và Qdrant Cloud đã đầy đủ dữ liệu.")

if __name__ == "__main__":
    main()
