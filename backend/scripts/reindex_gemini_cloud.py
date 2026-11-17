"""
Script tái nhúng (Re-index) toàn bộ 5.758 điều khoản trên Qdrant Cloud bằng Google Gemini Embedding.
Thay thế dense vector cũ (BGE-M3) bằng Gemini vector 1024 chiều (gemini-embedding-001).
Giữ nguyên sparse vector, metadata và ID của từng point.

Chạy:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/reindex_gemini_cloud.py
"""
import sys
import time
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    GOOGLE_API_KEYS,
)
from app.services.embedding.gemini import GeminiEmbedding

BATCH_SIZE = 50  # 50 texts per Gemini batchEmbedContents call

def main():
    print("=" * 70)
    print("🚀 BẮT ĐẦU TÁI NHÚNG DỮ LIỆU LÊN QDRANT CLOUD BẰNG GOOGLE GEMINI (1024D)")
    print("=" * 70)

    # 1. Khởi tạo Gemini Embedding Adapter
    print("\n[1/3] Khởi tạo Google Gemini Embedding Adapter...")
    gemini_emb = GeminiEmbedding(dimension=1024, batch_size=BATCH_SIZE)
    print("  ✅ Gemini Embedding sẵn sàng (outputDimension: 1024)")

    # 2. Kết nối Qdrant Cloud
    print("\n[2/3] Kết nối tới Qdrant Cloud...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
    coll_info = client.get_collection(QDRANT_COLLECTION)
    total_points = coll_info.points_count
    print(f"  ✅ Qdrant Cloud kết nối thành công: Collection '{QDRANT_COLLECTION}' có {total_points} points.")

    # 3. Lấy dữ liệu theo lô, tạo vector mới và cập nhật
    print(f"\n[3/3] Đang tiến hành tạo vector mới và cập nhật {total_points} points theo lô {BATCH_SIZE}...")
    start_time = time.time()
    offset = None
    processed = 0

    while True:
        records, next_offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=BATCH_SIZE,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )

        if not records:
            break

        # Chuẩn bị nội dung văn bản để nhúng
        batch_texts = []
        for r in records:
            text = r.payload.get("text_for_embedding") or r.payload.get("content") or ""
            batch_texts.append(text if text.strip() else "điều khoản luật")

        # Gọi Google Gemini Embedding API
        new_dense_vectors = gemini_emb.embed_documents(batch_texts)

        # Tạo danh sách points cập nhật
        updated_points = []
        for r, dense_vec in zip(records, new_dense_vectors):
            # Giữ nguyên sparse vector nếu có
            current_vector = r.vector
            if isinstance(current_vector, dict):
                vector_dict = {
                    "text-dense": dense_vec,
                    "text-sparse": current_vector.get("text-sparse"),
                }
            else:
                vector_dict = {"text-dense": dense_vec}

            updated_points.append(
                qdrant_models.PointStruct(
                    id=r.id,
                    vector=vector_dict,
                    payload=r.payload,
                )
            )

        # Upsert đè lên Qdrant Cloud
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=updated_points,
            wait=True,
        )

        processed += len(records)
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        print(f"  • Tiến độ: {processed}/{total_points} điều khoản ({processed/total_points*100:.1f}%) | {rate:.1f} điểm/s")

        if next_offset is None:
            break
        offset = next_offset

    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"🎉 HOÀN TẤT TÁI NHÚNG {processed} ĐIỀU KHOẢN TRONG {total_time:.1f} GIÂY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
