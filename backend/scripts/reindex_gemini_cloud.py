"""
Clone & Resumable script để tạo collection Qdrant cho chế độ Cloud (Google Gemini Embedding 1024d).

- Đọc từ collection nguồn (mặc định: vietlaw_clauses) ở chế độ READ-ONLY, không bao giờ ghi đè bản gốc BGE-M3.
- Tạo collection đích (mặc định: vietlaw_clauses_gemini) với named vectors text-dense (1024d Cosine)
  và text-sparse (IDF), kèm payload indexes dạng keyword cho 'category' và 'law_id'.
- Tự động bỏ qua các point ID đã tồn tại trong collection đích để chạy nối tiếp (resumable) an toàn
  khi gặp giới hạn quota Google Free Tier (1.000 RPD/key).

Chạy:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/reindex_gemini_cloud.py
    cd backend && PYTHONPATH=. .venv/bin/python scripts/reindex_gemini_cloud.py --dry-run
    cd backend && PYTHONPATH=. .venv/bin/python scripts/reindex_gemini_cloud.py --source vietlaw_clauses --target vietlaw_clauses_gemini --batch-size 50
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import EMBEDDING_DIMENSION, QDRANT_API_KEY, QDRANT_URL
from app.services.embedding.errors import EmbeddingServiceError
from app.services.embedding.gemini import GeminiEmbedding


def _ensure_target_collection(client: QdrantClient, target: str, dimension: int) -> None:
    if not client.collection_exists(target):
        print(f"  • Tạo mới collection '{target}' (text-dense {dimension}d Cosine + text-sparse IDF)...")
        client.create_collection(
            collection_name=target,
            vectors_config={
                "text-dense": qdrant_models.VectorParams(
                    size=dimension,
                    distance=qdrant_models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "text-sparse": qdrant_models.SparseVectorParams(
                    modifier=qdrant_models.Modifier.IDF,
                )
            },
        )

    for field_name in ("category", "law_id"):
        client.create_payload_index(
            collection_name=target,
            field_name=field_name,
            field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone Qdrant BGE-M3 collection sang collection Gemini Embedding (resumable)."
    )
    parser.add_argument("--source", default="vietlaw_clauses", help="Collection nguồn (chỉ đọc).")
    parser.add_argument("--target", default="vietlaw_clauses_gemini", help="Collection đích cho Gemini.")
    parser.add_argument("--batch-size", type=int, default=50, help="Số điều khoản mỗi lô (1..100).")
    parser.add_argument("--limit", type=int, default=0, help="Giới hạn số điểm mới tối đa trong lần chạy này (0 = không giới hạn).")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ kiểm tra số điểm còn thiếu, không gọi Gemini API.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.strip()
    target = args.target.strip()
    batch_size = max(1, min(args.batch_size, 100))

    if source == target:
        print("❌ Lỗi: --source và --target phải khác nhau để bảo toàn collection BGE-M3 gốc.")
        return 1

    print("=" * 72)
    print(f"🚀 CLONE & RESUMABLE RE-INDEX: '{source}' -> '{target}' (Gemini {EMBEDDING_DIMENSION}d)")
    print("=" * 72)

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=60)
    if not client.collection_exists(source):
        print(f"❌ Không tìm thấy collection nguồn '{source}' trên Qdrant.")
        return 1

    source_total = client.get_collection(source).points_count or 0
    print(f"[1/3] Collection nguồn '{source}': {source_total} points.")

    if not args.dry_run:
        _ensure_target_collection(client, target, EMBEDDING_DIMENSION)

    target_exists = client.collection_exists(target)
    existing_before = (client.get_collection(target).points_count or 0) if target_exists else 0
    print(f"[2/3] Collection đích '{target}': {existing_before}/{source_total} points đã có sẵn.")

    gemini_emb = None if args.dry_run else GeminiEmbedding(dimension=EMBEDDING_DIMENSION, batch_size=batch_size)

    print(f"[3/3] Bắt đầu quét nguồn theo lô {batch_size}...")
    start_time = time.time()
    offset = None
    scanned = 0
    skipped = 0
    embedded_now = 0
    missing_count = 0

    try:
        while True:
            records, next_offset = client.scroll(
                collection_name=source,
                limit=batch_size,
                offset=offset,
                with_vectors=not args.dry_run,
                with_payload=not args.dry_run,
            )
            if not records:
                break

            scanned += len(records)
            batch_ids = [r.id for r in records]
            if target_exists:
                already_present = {
                    p.id
                    for p in client.retrieve(
                        collection_name=target,
                        ids=batch_ids,
                        with_vectors=False,
                        with_payload=False,
                    )
                }
            else:
                already_present = set()

            pending_records = [r for r in records if r.id not in already_present]
            skipped += len(records) - len(pending_records)

            if pending_records:
                if args.limit > 0:
                    remaining_budget = args.limit - embedded_now
                    if remaining_budget <= 0:
                        break
                    pending_records = pending_records[:remaining_budget]

                if args.dry_run:
                    missing_count += len(pending_records)
                else:
                    batch_texts = []
                    for r in pending_records:
                        payload = r.payload or {}
                        text = payload.get("text_for_embedding") or payload.get("content") or ""
                        batch_texts.append(text if text.strip() else "điều khoản luật")

                    new_dense_vectors = gemini_emb.embed_documents(batch_texts)

                    upserts = []
                    for r, dense_vec in zip(pending_records, new_dense_vectors):
                        current_vector = r.vector
                        if isinstance(current_vector, dict) and current_vector.get("text-sparse") is not None:
                            vector_dict = {
                                "text-dense": dense_vec,
                                "text-sparse": current_vector["text-sparse"],
                            }
                        else:
                            vector_dict = {"text-dense": dense_vec}

                        upserts.append(
                            qdrant_models.PointStruct(
                                id=r.id,
                                vector=vector_dict,
                                payload=r.payload,
                            )
                        )

                    client.upsert(collection_name=target, points=upserts, wait=True)
                    embedded_now += len(upserts)
                    elapsed = max(time.time() - start_time, 1e-6)
                    print(
                        f"  • Đã thêm mới: {embedded_now} | Bỏ qua sẵn có: {skipped} "
                        f"| Quét: {scanned}/{source_total} ({scanned / max(source_total, 1) * 100:.1f}%) "
                        f"| Tốc độ: {embedded_now / elapsed:.1f} điểm/s"
                    )

            if args.limit > 0 and embedded_now >= args.limit:
                print(f"⏹ Đạt giới hạn --limit={args.limit}, dừng an toàn.")
                break

            if next_offset is None:
                break
            offset = next_offset

    except EmbeddingServiceError as exc:
        print(f"\n⚠️ Tạm dừng do lỗi/hết quota Gemini API: {exc}")
        print(
            f"   Tiến độ đã lưu an toàn vào '{target}': +{embedded_now} mới "
            f"(bỏ qua {skipped} đã có). Bạn có thể chạy lại script để nối tiếp."
        )
        return 2

    if args.dry_run:
        print(f"\n🔎 DRY-RUN: Đã có {skipped}/{source_total}, còn thiếu {missing_count} points cần nhúng.")
        return 0

    final_count = client.get_collection(target).points_count or 0
    total_time = time.time() - start_time
    print("\n" + "=" * 72)
    print(
        f"🎉 HOÀN TẤT: '{target}' hiện có {final_count}/{source_total} points "
        f"(+{embedded_now} mới trong {total_time:.1f}s)."
    )
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
