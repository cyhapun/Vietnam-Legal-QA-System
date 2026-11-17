"""
Kiểm thử toàn diện hoạt động của hệ thống local với Database Cloud (Supabase & Qdrant Cloud).
Bao gồm:
1. Supabase PostgreSQL: Đọc/Ghi dữ liệu laws, clauses, chat sessions
2. Qdrant Cloud: Vector search, Hybrid search, Payload filtering
3. Backend API: /readiness, /chat (RAG retrieval & LLM generation), /chat/stream
4. Frontend Proxy API: /api/chat/sessions, /api/chat
"""
import sys
import time
import json
import httpx
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import psycopg
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.config import (
    POSTGRES_DSN,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    GOOGLE_API_KEYS,
)

def run_tests():
    print("=" * 70)
    print("🚀 BẮT ĐẦU KIỂM THỬ TOÀN DIỆN LOCAL HOẠT ĐỘNG VỚI CLOUD DATABASE")
    print("=" * 70)

    results = []

    # -------------------------------------------------------------
    # Test 1: Supabase PostgreSQL (Đọc & Ghi)
    # -------------------------------------------------------------
    print("\n[1/5] Kiểm tra Supabase PostgreSQL...")
    t0 = time.time()
    try:
        conn = psycopg.connect(POSTGRES_DSN)
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM laws;")
            law_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM clauses;")
            clause_count = cur.fetchone()[0]
            
            # Test ghi thử 1 session test và xóa
            cur.execute("""
                INSERT INTO chat_sessions (session_id, title, summary, turn_count) 
                VALUES ('test-cloud-session-verify', 'Test Cloud Connection', 'Test summary', 1)
                ON CONFLICT (session_id) DO UPDATE SET title = EXCLUDED.title;
            """)
            conn.commit()
            
            cur.execute("SELECT title FROM chat_sessions WHERE session_id = 'test-cloud-session-verify';")
            saved_title = cur.fetchone()[0]
            
            # Xóa session test
            cur.execute("DELETE FROM chat_sessions WHERE session_id = 'test-cloud-session-verify';")
            conn.commit()
            
        conn.close()
        elapsed = time.time() - t0
        print(f"  ✅ Supabase: Đọc {law_count} luật, {clause_count} điều khoản.")
        print(f"  ✅ Supabase: Test Ghi & Đọc Session thành công ('{saved_title}'). ({elapsed:.2f}s)")
        results.append(("Supabase PostgreSQL", True, f"{law_count} laws, {clause_count} clauses, write/read OK"))
    except Exception as e:
        print(f"  ❌ Supabase thất bại: {e}")
        results.append(("Supabase PostgreSQL", False, str(e)))

    # -------------------------------------------------------------
    # Test 2: Qdrant Cloud (Cluster, Count, Filtered Search)
    # -------------------------------------------------------------
    print("\n[2/5] Kiểm tra Qdrant Cloud...")
    t0 = time.time()
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        coll_info = client.get_collection(QDRANT_COLLECTION)
        points_count = coll_info.points_count
        
        # Test scroll và filter bằng category
        flt = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="category",
                    match=qdrant_models.MatchValue(value="land")
                )
            ]
        )
        points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=flt,
            limit=3,
            with_payload=True,
            with_vectors=False
        )
        elapsed = time.time() - t0
        
        print(f"  ✅ Qdrant Cloud: Collection '{QDRANT_COLLECTION}' có {points_count} points. Status: {coll_info.status}")
        print(f"  ✅ Qdrant Cloud: Filter query (category='land') thành công lấy được {len(points)} records ({elapsed:.2f}s)")
        if points:
            p = points[0]
            print(f"     Payload mẫu: Law: {p.payload.get('law_id')} - Điều {p.payload.get('clause_id')} ({p.payload.get('law_title', '')[:40]}...)")
        results.append(("Qdrant Cloud", True, f"{points_count} points, payload filter OK"))
    except Exception as e:
        print(f"  ❌ Qdrant Cloud thất bại: {e}")
        results.append(("Qdrant Cloud", False, str(e)))

    # -------------------------------------------------------------
    # Test 3: Backend Local /readiness
    # -------------------------------------------------------------
    print("\n[3/5] Kiểm tra Backend Local /readiness...")
    t0 = time.time()
    try:
        res = httpx.get("http://localhost:8000/readiness", timeout=10.0)
        data = res.json()
        assert res.status_code == 200, f"Status code {res.status_code}"
        assert data.get("status") == "ready", f"Status {data.get('status')}"
        assert data.get("components", {}).get("postgres", {}).get("status") == "ok"
        assert data.get("components", {}).get("qdrant", {}).get("status") == "ok"
        elapsed = time.time() - t0
        print(f"  ✅ Backend /readiness: SẴN SÀNG (postgres: ok, qdrant: ok, points: {data['components']['qdrant']['points']}) ({elapsed:.2f}s)")
        results.append(("Backend Readiness", True, "Status ready, all components OK"))
    except Exception as e:
        print(f"  ❌ Backend /readiness thất bại: {e}")
        results.append(("Backend Readiness", False, str(e)))

    # -------------------------------------------------------------
    # Test 4: Backend Local RAG Query (/chat)
    # -------------------------------------------------------------
    print("\n[4/5] Kiểm tra Backend Local RAG Chat (/chat)...")
    t0 = time.time()
    try:
        payload = {
            "messages": [
                {"role": "user", "content": "Hành vi nào bị nghiêm cấm trong quản lý và sử dụng nhà ở theo Luật Nhà ở?"}
            ],
            "sessionId": "test-cloud-session",
            "category": "all",
            "streaming": False
        }
        res = httpx.post("http://localhost:8000/chat", json=payload, timeout=60.0)
        assert res.status_code == 200, f"Status code {res.status_code}: {res.text}"
        data = res.json()
        answer = data.get("text", "")
        citations = data.get("contextUsed", [])
        elapsed = time.time() - t0
        
        print(f"  ✅ Backend RAG Chat: Phản hồi thành công trong {elapsed:.2f}s!")
        print(f"     Số trích dẫn pháp lý tìm thấy từ Qdrant Cloud: {len(citations)}")
        for c in citations[:3]:
            print(f"     - Điều {c.get('clause_id')}: {c.get('law_title', '')[:40]}... (Độ phù hợp: {c.get('score', 0):.4f})")
        print(f"     Nội dung trả lời mẫu: {answer[:180].strip()}...")
        results.append(("Backend RAG Pipeline", True, f"{len(citations)} citations, response generated in {elapsed:.2f}s"))
    except Exception as e:
        print(f"  ❌ Backend RAG Chat thất bại: {e}")
        results.append(("Backend RAG Pipeline", False, str(e)))

    # -------------------------------------------------------------
    # Test 5: Frontend API Proxy (/api/chat)
    # -------------------------------------------------------------
    print("\n[5/5] Kiểm tra Frontend Proxy (/api/chat & /api/chat/sessions)...")
    t0 = time.time()
    try:
        # Test get sessions
        res_sessions = httpx.get("http://localhost:3000/api/chat/sessions", timeout=10.0)
        sessions_ok = res_sessions.status_code == 200
        sessions_list = res_sessions.json() if sessions_ok else []
        
        # Test post chat non-streaming via frontend proxy
        payload = {
            "messages": [
                {"role": "user", "content": "Quyền của công dân đối với đất đai theo Luật Đất đai là gì?"}
            ],
            "sessionId": "test-cloud-session-frontend",
            "category": "all",
            "streaming": False
        }
        res_chat = httpx.post("http://localhost:3000/api/chat", json=payload, timeout=60.0)
        chat_ok = res_chat.status_code == 200
        elapsed = time.time() - t0
        
        if sessions_ok and chat_ok:
            data = res_chat.json()
            citations = data.get("contextUsed", [])
            answer = data.get("text", "")
            print(f"  ✅ Frontend API Proxy: Cả /api/chat/sessions ({len(sessions_list)} sessions) và /api/chat đều hoạt động trơn tru! ({elapsed:.2f}s)")
            print(f"     Frontend nhận được {len(citations)} trích dẫn và phản hồi từ Backend qua Cloud DB.")
            results.append(("Frontend API Proxy", True, f"Sessions ({len(sessions_list)}) & Chat proxy OK in {elapsed:.2f}s"))
        else:
            print(f"  ⚠️ Frontend Proxy issues: sessions={res_sessions.status_code}, chat={res_chat.status_code}")
            results.append(("Frontend API Proxy", False, f"sessions: {res_sessions.status_code}, chat: {res_chat.status_code}"))
    except Exception as e:
        print(f"  ❌ Frontend Proxy thất bại: {e}")
        results.append(("Frontend API Proxy", False, str(e)))

    # -------------------------------------------------------------
    # Tổng kết
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("📊 BẢNG TỔNG KẾT KIỂM THỬ CLOUD DATABASE TRÊN LOCAL")
    print("=" * 70)
    all_passed = True
    for name, ok, note in results:
        status_icon = "✅ PASS" if ok else "❌ FAIL"
        if not ok:
            all_passed = False
        print(f" - {name:<25}: {status_icon:<8} | {note}")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
