"""
Script kiểm tra kết nối tới Database Cloud (Supabase PostgreSQL & Qdrant Cloud).
Chạy:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/test_cloud_connection.py
"""
import sys
import os
from urllib.parse import urlparse
from pathlib import Path

# Nạp cấu hình từ .env
from app.config import (
    POSTGRES_DSN,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    SEMANTIC_CACHE_COLLECTION,
    EMBEDDING_DIMENSION,
)

def print_banner(text: str):
    print("\n" + "=" * 65)
    print(f"  {text}")
    print("=" * 65)

def test_supabase_postgres():
    print("\n[1/2] 🔍 Đang kiểm tra kết nối Supabase (PostgreSQL)...")
    try:
        import psycopg
    except ImportError:
        try:
            import psycopg2 as psycopg
        except ImportError:
            print("  ❌ Lỗi: Chưa cài đặt thư viện 'psycopg' hoặc 'psycopg2'.")
            return False

    parsed = urlparse(POSTGRES_DSN)
    masked_dsn = POSTGRES_DSN
    if parsed.password:
        masked_dsn = POSTGRES_DSN.replace(parsed.password, "******")

    print(f"  • Host: {parsed.hostname}")
    print(f"  • Port: {parsed.port or 5432}")
    print(f"  • Database: {(parsed.path or '').lstrip('/')}")
    print(f"  • DSN: {masked_dsn}")

    try:
        connect_kwargs = {}
        if psycopg.__name__ == "psycopg":
            connect_kwargs["connect_timeout"] = 10

        conn = psycopg.connect(POSTGRES_DSN, **connect_kwargs)
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"  ✅ Kết nối PostgreSQL thành công!")
            print(f"     Phiên bản: {version.split(',')[0]}")

            # Kiểm tra các bảng đã tồn tại
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('laws', 'clauses', 'chat_sessions', 'chat_messages', 'chat_feedbacks');
            """)
            existing_tables = [row[0] for row in cur.fetchall()]
            if existing_tables:
                print(f"     Các bảng hiện có: {', '.join(existing_tables)}")
            else:
                print("     ℹ️ Cơ sở dữ liệu chưa có bảng của VietLaw. Đang tự động khởi tạo bảng schema...")
                from app.services.storage import _ensure_schema
                _ensure_schema()
                print("     ✅ Đã tự động khởi tạo đầy đủ các bảng schema (laws, clauses, chat_sessions...)")

        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ Kết nối PostgreSQL THẤT BẠI:")
        print(f"     Lỗi: {e}")
        if "timeout" in str(e).lower():
            print("     💡 Mẹo: Với Supabase, hãy ưu tiên dùng connection string dạng 'Connection Pooling' (port 6543 hoặc 5432 của pooler) và thêm parameter '?sslmode=require'.")
        return False

def test_qdrant_cloud():
    print("\n[2/2] 🔍 Đang kiểm tra kết nối Qdrant Cloud (Vector Database)...")
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        print("  ❌ Lỗi: Chưa cài đặt thư viện 'qdrant_client'.")
        return False

    parsed = urlparse(QDRANT_URL)
    print(f"  • Host: {parsed.hostname}")
    print(f"  • Port: {parsed.port or (443 if parsed.scheme == 'https' else 6333)}")
    print(f"  • API Key: {'Đã cấu hình (******)' if QDRANT_API_KEY else 'Không có (Dùng cho local)'}")

    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY or None,
            timeout=10,
        )
        collections_resp = client.get_collections()
        col_names = [c.name for c in collections_resp.collections]
        print(f"  ✅ Kết nối Qdrant thành công!")
        print(f"     Danh sách Collections hiện có: {col_names if col_names else '(Chưa có collection nào)'}")

        if QDRANT_COLLECTION in col_names:
            info = client.get_collection(QDRANT_COLLECTION)
            points = getattr(info, "points_count", 0)
            status = getattr(info, "status", "unknown")
            print(f"     ✅ Collection '{QDRANT_COLLECTION}' đã sẵn sàng:")
            print(f"        - Số lượng vector (points): {points}")
            print(f"        - Trạng thái collection: {status}")
        else:
            print(f"     ℹ️ Collection '{QDRANT_COLLECTION}' chưa tồn tại trên cluster này.")
            print(f"        Bạn có thể chạy script 'ingest_to_storage.py' để nạp và tạo collection.")

        return True
    except Exception as e:
        print(f"  ❌ Kết nối Qdrant THẤT BẠI:")
        print(f"     Lỗi: {e}")
        if "401" in str(e) or "forbidden" in str(e).lower():
            print("     💡 Mẹo: Kiểm tra lại QDRANT_API_KEY xem đã copy đúng từ Qdrant Cloud chưa.")
        return False

def main():
    print_banner("KIỂM TRA KẾT NỐI DATABASE CLOUD (VIETLAW AI)")
    pg_ok = test_supabase_postgres()
    qd_ok = test_qdrant_cloud()

    print_banner("KẾT QUẢ TỔNG QUAN")
    print(f"  • Supabase (PostgreSQL) : {'✅ SẴN SÀNG' if pg_ok else '❌ CHƯA KẾT NỐI ĐƯỢC'}")
    print(f"  • Qdrant (Vector DB)    : {'✅ SẴN SÀNG' if qd_ok else '❌ CHƯA KẾT NỐI ĐƯỢC'}")

    if pg_ok and qd_ok:
        print("\n🎉 Tuyệt vời! Cả 2 database cloud đều đã sẵn sàng kết nối.")
        print("   Bạn có thể yên tâm đưa các biến môi trường này lên Vercel!")
        sys.exit(0)
    else:
        print("\n⚠️ Vui lòng kiểm tra lại thông tin kết nối trong file .env trước khi cấu hình trên Vercel.")
        sys.exit(1)

if __name__ == "__main__":
    main()
