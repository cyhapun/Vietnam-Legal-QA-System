# Design: Migrate Embedding Pipeline to Google Gemini Embeddings

## 1. Context & Architecture Overview

VietLaw AI chuyển đổi từ kiến trúc đa nhà cung cấp (Hybrid Providers: Google LLM + HuggingFace Embedding) sang kiến trúc hợp nhất **Unified Google AI Stack**:

```
                                  KIẾN TRÚC HỢP NHẤT
                               
                               ┌─────────────────────────┐
                               │  Người dùng / Frontend  │
                               └────────────┬────────────┘
                                            │ Query
                                            ▼
                               ┌─────────────────────────┐
                               │     FastAPI Backend     │
                               └──────┬───────────┬──────┘
                                      │           │
                 1. Embed Query (1024d)│           │ 2. Hybrid Search
                                      ▼           ▼
                         ┌─────────────────┐  ┌──────────────────┐
                         │ Google AI Studio│  │   Qdrant Cloud   │
                         │ gemini-embedding│  │ vietlaw_clauses  │
                         │    (1024d)      │  │ (Dense: 1024d    │
                         └─────────────────┘  │  Sparse: BM25)   │
                                              └────────┬─────────┘
                                                       │
                                        3. Get Clauses │
                                                       ▼
                                              ┌──────────────────┐
                                              │  Supabase Cloud  │
                                              │ (PostgreSQL 17)  │
                                              └──────────────────┘
```

---

## 2. Technical Specification

### 2.1 Gemini Embedding Adapter (`backend/app/services/embedding/gemini.py`)
- Kế thừa giao diện chuẩn `BaseEmbedding`.
- **API Endpoints:**
  - `embedContent`: Cho câu hỏi người dùng (`embed_query`), truyền tham số:
    ```json
    {
      "model": "models/gemini-embedding-001",
      "content": {"parts": [{"text": "..."}]},
      "taskType": "RETRIEVAL_QUERY",
      "outputDimensionality": 1024
    }
    ```
  - `batchEmbedContents`: Cho danh sách tài liệu (`embed_documents`), batch size tối đa 100 texts/lần gọi:
    ```json
    {
      "requests": [
        {
          "model": "models/gemini-embedding-001",
          "content": {"parts": [{"text": "..."}]},
          "taskType": "RETRIEVAL_DOCUMENT",
          "outputDimensionality": 1024
        }
      ]
    }
    ```
- **Xoay vòng Key (Failover):** Sử dụng hàm `parse_google_api_keys()` từ `app.services.llm` để tự động đổi sang key kế tiếp khi gặp HTTP 429 hoặc lỗi quota.

### 2.2 Quản Lý Cấu Hình (`backend/app/config.py`)
- Bổ sung `EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini").strip().lower()`.
- Hỗ trợ giá trị `"gemini"` trong `HUGGINGFACE_EMBEDDING_MODE` hoặc qua cờ cấu hình `EMBEDDING_PROVIDER`.
- `EMBEDDING_DIMENSION = 1024` (giữ nguyên không đổi).
- Cập nhật hàm `validate_runtime_configuration()` để cho phép `gemini` hoạt động hợp lệ ở cả profile `local` và `serverless`.

### 2.3 Script Tái Nhúng Dữ Liệu (`backend/scripts/reindex_gemini_cloud.py`)
1. Kết nối PostgreSQL Supabase để đọc danh sách 5.758 điều khoản.
2. Xử lý chia lô theo kích thước batch = 100 clauses.
3. Gửi batch lên Gemini API `batchEmbedContents` với `outputDimensionality: 1024` và `taskType: RETRIEVAL_DOCUMENT`.
4. Giữ nguyên sparse vector và metadata của từng điều khoản.
5. Upsert batch các điểm vector vào collection `vietlaw_clauses` trên Qdrant Cloud.
6. Xác minh số lượng điểm và tính hợp lệ của payload index.

### 2.4 Cập Nhật Vercel & Môi Trường
- `vercel.json`: Đổi cấu hình embedding sang provider Google Gemini (`EMBEDDING_PROVIDER: "gemini"`).
- `.env` & `.env.example`: Dọn dẹp biến thừa `HUGGINGFACE_API_KEY`, hướng dẫn dùng `GOOGLE_API_KEYS`.
