# VietLaw AI - Hệ thống Hỏi đáp Pháp luật Việt Nam

Chatbot tra cứu pháp luật Việt Nam sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)**.  
Hệ thống truy xuất các điều khoản pháp luật liên quan từ cơ sở dữ liệu vector, sau đó dùng LLM để sinh câu trả lời có trích dẫn căn cứ pháp lý chính xác.

> **Project môn học:** Introduction to Machine Learning

## Danh sách thành viên

| Mã số sinh viên | Họ tên |
|---|---|
| 23120283 | Phạm Quốc Khánh |
| 23120301 | Phạm Thành Nam |
| 23120318 | Trương Quang Phát |
| 23120329 | Châu Huỳnh Phúc (Trưởng nhóm) |
| 23120334 | Huỳnh Tấn Phước |

---

## Mục lục

- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Hướng dẫn cài đặt và chạy](#hướng-dẫn-cài-đặt-và-chạy)
- [Kỹ thuật sử dụng](#kỹ-thuật-sử-dụng)
- [Tính năng](#tính-năng)
- [Dữ liệu pháp luật](#dữ-liệu-pháp-luật)
- [Công nghệ](#công-nghệ)
- [Local model integration](docs/local_model_integration.md)

---

## Kiến trúc hệ thống

Hệ thống theo mô hình **Client-Server** với 2 thành phần chính giao tiếp qua REST API:

```text
  NGƯỜI DÙNG
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 15)                  │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Sidebar  │  │ChatInterface │  │ ProviderSelector │   │
│  │(lịch sử) │  │  (giao diện) │  │  (chọn model)    │   │
│  └──────────┘  └──────┬───────┘  └──────────────────┘   │
│                       │                                 │
│               POST /api/chat                            │
│               ┌───────▼────────┐                        │
│               │ API Route Proxy│ ← Next.js API Route    │
│               └───────┬────────┘                        │
└───────────────────────┼─────────────────────────────────┘
                        │ HTTP POST (JSON)
┌───────────────────────▼─────────────────────────────────┐
│                 BACKEND (FastAPI + Python)              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ app/api/chat.py          → Xử lý request        │    │
│  │ app/services/pipeline.py → RAG Orchestrator     │    │
│  │ app/services/search/     → FAISS, BM25, Hybrid  │    │
│  │ app/services/reranking/  → CrossEncoder         │    │
│  │ app/config.py            → Cấu hình Ablation    │    │
│  └─────────────────────────────────────────────────┘    │
│       │                                                 │
│       │ Local fine-tuned embedding + Qdrant Cloud       │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────┐        │
│  │ Embedding: fine-tuned BGE-M3 local artifact │        │
│  │ Reranker: fine-tuned local cross-encoder    │        │
│  │ LLM: Gemini / configured remote provider    │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Luồng xử lý chính

1. **User** nhập câu hỏi pháp lý → Frontend gửi `POST /api/chat`
2. **Next.js API Route** (proxy) chuyển tiếp request đến Backend FastAPI
3. **Backend** dùng Qdrant Hybrid Search (Dense Vector + Sparse Vector BM25) với RRF để tìm các điều khoản liên quan
4. Hàm `build_nested_context()` xây dựng **context 2 cấp** (dẫn chiếu đệ quy giữa các điều luật)
5. Context + **Tóm tắt bối cảnh cũ** (từ Memory Manager) + lịch sử chat ngắn + câu hỏi → **System Prompt** → gọi LLM qua HuggingFace API
6. The LLM generates the answer, then the backend persists the complete `user/assistant` message pair to PostgreSQL before the turn is considered complete.
7. The backend returns `{text, contextUsed}` or emits the final SSE `done` event; the frontend renders Markdown and legal context references.
8. A background task only summarizes conversation memory after the completed turn has been persisted.

---

## Cấu trúc dự án

```text
Vietnam-Legal-QA-System/
│
├── .env.example                 # Template biến môi trường
├── .gitignore                   # Git ignore rules
├── README.md                    # Tài liệu dự án (file này)
├── docker-compose.yml           # Docker Compose cho phát triển
│
├── backend/                     # === BACKEND (Python + FastAPI) ===
│   ├── main.py                  # Entry point — chạy: python main.py
│   ├── rag_service.py           # Backward-compatible shim
│   ├── requirements.txt         # Dependencies Python
│   ├── embedded_files.json      # Tracking các file đã embedding
│   │
│   ├── app/                     # Package chính (modular)
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory + startup events
│   │   ├── config.py            # Cấu hình tập trung (paths, API keys, constants)
│   │   ├── models.py            # Pydantic schemas (ChatRequest, ChatResponse)
│   │   │
│   │   ├── api/                 # API Layer
│   │   │   └── chat.py          # Router POST /chat — xử lý request/response
│   │   │
│   │   ├── services/            # Business Logic Layer
│   │   │   ├── pipeline.py      # Orchestrator kết nối các module (Ablation study)
│   │   │   ├── storage.py       # Quản lý Database (PostgreSQL + Qdrant)
│   │   │   ├── knowledge_base.py# In-memory KB fallback
│   │   │   ├── llm.py           # Kết nối LLM (HuggingFace) + System Prompt
│   │   │   ├── search/          # Search modules: Qdrant, FAISS fallback
│   │   │   ├── reranking/       # Reranking modules: NoRerank, CrossEncoder
│   │   │   ├── context_builder/ # Context building (Nested 2-level)
│   │   │   ├── chunking/        # Document chunking (Clause-based)
│   │   │   ├── sparse_vector.py # Sinh Sparse Vectors cho BM25 (TF) tiếng Việt
│   │   │   └── embedding/       # Text Embedding (HuggingFace API)
│   │   │
│   │   └── utils/               # Utilities
│   │       └── logging.py       # Logging chuẩn
│   │
│   ├── data/
│   │   ├── processed/           # 8 file JSON dữ liệu pháp luật đã tiền xử lý
│   │   └── raw/                 # Dữ liệu thô (chưa có)
│   │
│   └── vietlaw_faiss_index/     # FAISS vector index (22.5 MB)
│       ├── index.faiss          # Vector data
│       └── index.pkl            # Metadata
│
├── frontend/                    # === FRONTEND (Next.js 15 + React 19) ===
│   ├── package.json             # Dependencies Node.js
│   ├── next.config.ts           # Cấu hình Next.js
│   ├── tsconfig.json            # Cấu hình TypeScript
│   ├── postcss.config.mjs       # PostCSS + TailwindCSS
│   │
│   ├── app/                     # Next.js App Router
│   │   ├── layout.tsx           # Root layout (metadata, global styles)
│   │   ├── page.tsx             # Trang chính — render ChatInterface
│   │   ├── globals.css          # CSS toàn cục + custom scrollbar
│   │   └── api/chat/
│   │       └── route.ts         # API Route Proxy → chuyển tiếp đến Backend
│   │
│   ├── components/              # React Components
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx    # Giao diện chat chính
│   │   │   ├── ChatMessage.tsx      # Hiển thị tin nhắn + căn cứ pháp lý
│   │   │   ├── ProviderSelector.tsx # Dropdown chọn model AI
│   │   │   └── Sidebar.tsx          # Sidebar quản lý phiên chat
│   │   └── ui/
│   │       └── LoadingSpinner.tsx   # Animation loading khi chờ LLM
│   │
│   ├── hooks/                   # Custom React Hooks
│   │   ├── use-chat-sessions.ts # Quản lý sessions
│   │   ├── use-click-outside.ts # Đóng dropdown khi click ngoài
│   │   └── use-mobile.ts        # Phát hiện thiết bị mobile
│   │
│   └── lib/                     # Shared Utilities
│       ├── types.ts             # TypeScript interfaces
│       ├── constants.ts         # Hằng số (models, categories, storage keys)
│       └── utils.ts             # Hàm tiện ích (class merging)
│
└── notebooks/                   # === JUPYTER NOTEBOOKS ===
    └── embedding_model.ipynb    # Notebook thử nghiệm embedding model
```

### Giải thích thiết kế

| Layer | Vai trò | Files |
|---|---|---|
| **API Layer** | Nhận HTTP request, validate, trả response | `api/chat.py`, `models.py` |
| **Service Layer** | Business logic: RAG, LLM, Vector DB | `services/llm.py`, `pipeline.py`, `storage.py` |
| **Config Layer** | Quản lý cấu hình, env, paths | `config.py` |
| **Utils Layer** | Tiện ích dùng chung | `utils/logging.py` |

> **Nguyên tắc:** Mỗi file **một nhiệm vụ duy nhất** (Single Responsibility). API layer không chứa business logic, service layer không biết về HTTP.

---

## Hướng dẫn Cài đặt và Chạy

### Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Google/OpenAI-compatible LLM key | Dùng cho phần sinh câu trả lời từ provider remote |

### Bước 1: Clone và cấu hình

```bash
# Clone repository
git clone https://github.com/cyhapun/Vietnam-Legal-QA-System.git
cd Vietnam-Legal-QA-System

# Tạo file biến môi trường từ template
cp .env.example .env

# .env contains server defaults and infrastructure settings.
# Runtime provider/model API keys are configured in the web UI.
#
# Query embeddings are generated by the fine-tuned local model for retrieval consistency:
# EMBEDDING_PROVIDER=huggingface
# HUGGINGFACE_EMBEDDING_MODE=local
# HUGGINGFACE_EMBEDDING_MODEL=../models/embedding/vietlaw-bge-m3-finetuned/best
# HUGGINGFACE_API_KEY can stay empty in local embedding/reranking mode.
#
# PostgreSQL is local; Qdrant may be Qdrant Cloud if the collection was
# already built with the same fine-tuned embedding model:
# STORAGE_BACKEND=qdrant_postgres
# POSTGRES_DSN=postgresql://postgres:postgres@localhost:15432/vietlaw
# QDRANT_URL=
# QDRANT_API_KEY=
# QDRANT_COLLECTION=vietlaw_clauses
#
# Optional server fallback defaults:
# GOOGLE_API_KEY=
# ENABLE_GOOGLE_FALLBACK=false
# INFERENCE_STRATEGY=remote_first
# remote_first never falls back to local Ollama.
```

### Bước 2: Chạy Backend (Terminal 1)

```bash
# Di chuyển vào thư mục backend
cd backend

# (Tùy chọn) Tạo virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt

# Khởi chạy server
python main.py
# Server chạy tại: http://localhost:8000
```

### Bước 2a: Chạy với PostgreSQL + Qdrant (tùy chọn)

```bash
# Từ thư mục root project
docker compose up -d postgres qdrant

# Trong backend, dùng storage backend database-backed
# .env
# STORAGE_BACKEND=qdrant_postgres

# Sau đó chạy ingestion một lần
python scripts/ingest_to_storage.py
```

> Nếu dịch vụ database chưa sẵn sàng, backend vẫn sẽ khởi động bằng fallback FAISS và ghi log cảnh báo. Nếu Docker Desktop hoặc Docker Engine chưa chạy, lệnh `docker compose up -d postgres qdrant` sẽ thất bại trước khi backend có thể dùng PostgreSQL/Qdrant.
> **Lưu ý quan trọng:** Phải chạy từ **thư mục `backend/`**, không phải từ thư mục root!

### Bước 3: Chạy Frontend (Terminal 2)

```bash
# Mở terminal MỚI, di chuyển vào thư mục frontend
cd frontend

# Cài đặt dependencies
npm install

# Khởi chạy dev server
npm run dev
# Mở trình duyệt tại: http://localhost:3000
```

### Chạy bằng Docker (Tùy chọn)

```bash
# Từ thư mục root project
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Lưu ý khi chạy

- **Backend phải chạy TRƯỚC Frontend** — Frontend proxy request đến Backend.
- **FAISS index đã có sẵn** trong repo (22.5 MB) — không cần re-embed dữ liệu.
- **Lần đầu khởi động** Backend sẽ nạp 8 file JSON vào RAM + tải FAISS index (~5-10 giây).
- Khi bật `STORAGE_BACKEND=qdrant_postgres`, backend sẽ tạo schema PostgreSQL và collection Qdrant tại startup.
- Dữ liệu sẽ **không tự động được nhúng (embed)** khi khởi động backend để tăng tốc độ.
- Để **nạp dữ liệu ban đầu hoặc nạp lại (re-embed) dữ liệu mới**, bạn PHẢI chạy script thủ công: `python scripts/ingest_to_storage.py`.

---

## Kỹ thuật sử dụng

### 1. RAG (Retrieval-Augmented Generation)

Kỹ thuật cốt lõi của hệ thống — **kết hợp truy xuất thông tin + sinh văn bản**:

```text
Câu hỏi → [Retriever] → Điều khoản liên quan → [LLM] → Câu trả lời có trích dẫn
```

**Tại sao dùng RAG?** LLM đơn thuần có thể tạo ra thông tin pháp lý không chính xác. RAG buộc LLM chỉ trả lời dựa trên dữ liệu thực tế được cung cấp, đảm bảo tính chính xác.

### 2. Qdrant Hybrid Search (Native Sparse Vectors)

Hệ thống sử dụng cơ sở dữ liệu vector tiên tiến (Qdrant) để thực hiện tìm kiếm kết hợp:
- **Dense Vector Search**: Semantic search qua fine-tuned BGE-M3 embedding local (1024 chiều), truy vấn collection Qdrant đã index cùng embedding space.
- **Sparse Vector Search (BM25)**: Tìm kiếm từ khóa chính xác (Exact Keyword Match) thông qua thuật toán sinh vector thưa tự xây dựng cho tiếng Việt.
- **Reciprocal Rank Fusion (RRF)**: Trộn 2 kết quả trực tiếp bên trong engine của Qdrant qua hàm `query_points` với nhiều khối `prefetch`, tối đa hóa tốc độ truy xuất và giải phóng hoàn toàn RAM.
- *(Dự phòng: Vẫn hỗ trợ FAISS cục bộ cho hệ thống không có Qdrant)*.

### 3. Cross-Encoder Reranking

Sau bước Search, kết quả có thể được xếp hạng lại (Reranking) để tăng độ chính xác:
- **CrossEncoderReranker**: Dùng fine-tuned BGE reranker local để đánh giá chi tiết (joint encoding) giữa Query và Document.
- Có thể bật/tắt dễ dàng qua config `PIPELINE_RERANKING=cross_encoder|none`.

### 4. MMR Retrieval (Maximal Marginal Relevance)

Thay vì chỉ lấy top-K kết quả giống nhau nhất, MMR **cân bằng giữa độ liên quan và đa dạng**:

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `k` | 6 | Trả về 6 điều khoản liên quan nhất |
| `fetch_k` | 20 | Lấy 20 ứng viên ban đầu rồi chọn 6 |
| `lambda_mult` | 0.8 | 80% ưu tiên liên quan, 20% ưu tiên đa dạng |

### 5. Nested Context Building (Dẫn chiếu 2 cấp)

Tính năng nổi bật — xây dựng **context đệ quy** giúp LLM hiểu liên kết giữa các điều luật:

```text
[Cấp 0] Điều khoản được retrieve → Hiển thị đầy đủ nội dung
   └── [Cấp 1] Dẫn chiếu từ Cấp 0 → Lấy toàn bộ content từ RAM
          └── [Cấp 2] Dẫn chiếu từ Cấp 1 → Chỉ lấy tóm tắt
```

**Ví dụ:** Điều 137 Luật Đất đai dẫn chiếu đến Điều 45 → hệ thống tự động lấy nội dung Điều 45 đưa vào context cho LLM.

### 6. Category-based Filtering

Lọc kết quả truy xuất theo **lĩnh vực pháp luật** để tăng độ chính xác:

- Tất cả các luật
- Dân sự
- Gia đình & Nhân thân
- Đất đai
- Bất động sản
- Xây dựng & Môi trường
- Giao thông
- Trật tự & Xử phạt

Metadata `law_id` và `category` được dùng để lọc document trước khi tìm kiếm.
Mỗi lựa chọn trên giao diện có thêm mô tả ngắn về phạm vi pháp luật tương ứng.

### 7. Prompt Engineering

System prompt được thiết kế với **4 quy tắc bắt buộc** cho LLM:
1. **Trích dẫn rõ ràng:** Luôn nêu tên Luật, Chương, Điều, Khoản.
2. **Xử lý dẫn chiếu:** Dùng nội dung dẫn chiếu để giải thích thuật ngữ.
3. **Không suy đoán:** Chỉ trả lời dựa trên dữ liệu được cung cấp.
4. **Ngôn ngữ:** Trả lời bằng tiếng Việt chuyên nghiệp, khách quan.

### 8. Cơ sở dữ liệu Persistent (Qdrant & PostgreSQL)

Thay vì tải toàn bộ index vào RAM, phiên bản mới nhất sử dụng kiến trúc lưu trữ vĩnh viễn:
- **PostgreSQL**: Lưu trữ metadata và nội dung nguyên bản của văn bản pháp luật, trạng thái ingest.
- **Qdrant**: Lưu trữ Named Vectors (`text-dense`, `text-sparse`) cho Hybrid Search hiệu suất cao.

Đảm bảo hệ thống có thể mở rộng lên hàng triệu điều luật mà không gây tràn bộ nhớ (OOM). Khởi động siêu tốc vì bỏ qua việc rebuild BM25 Index.

### Chat session persistence and refresh behavior

- `chat_sessions` and `chat_messages` are stored in PostgreSQL; browser storage is only used for active-session identity and fast UI recovery.
- A first visit without an active session opens a blank new-chat frame that is not persisted until the user sends a message.
- Refreshing while viewing an existing conversation restores that active session and keeps follow-up messages under the same `sessionId`.
- Historical conversations are lazy-loaded from PostgreSQL when selected in the sidebar.
- If browser cache is stale, the frontend reconciles it with PostgreSQL whenever `/chat/sessions` reports a larger `message_count`.
- The backend persists the complete user/assistant turn before returning `/chat` or emitting `/chat/stream` `done`, so immediate refreshes should still show both the question and response.

### 9. Hybrid Inference Policy

Hệ thống dùng biến môi trường `INFERENCE_STRATEGY` để chọn thứ tự provider:
- `remote_first`: chỉ dùng provider remote và các remote fallback đã cấu hình; không khởi tạo hoặc fallback sang Ollama local.
- `local_first`: dùng Ollama local trước, sau đó mới fallback sang provider remote nếu cấu hình cho phép.

Các lớp chính:
- **LLM Layer**: trong `remote_first`, chạy runtime/provider remote và Google fallback nếu bật; trong `local_first`, Ollama được dùng trước.
- **Embedding Layer**: với `HUGGINGFACE_EMBEDDING_MODE=local`, retrieval dùng fine-tuned embedding artifact trên filesystem. Lỗi artifact, dimension, Qdrant auth/schema hoặc missing collection được báo rõ; backend không fallback sang Hugging Face embedding API hoặc FAISS trừ khi được bật tường minh.
- **Reranking Layer**: với `PIPELINE_RERANKING=cross_encoder`, backend dùng fine-tuned cross-encoder local từ `RERANKER_MODEL`. Nếu artifact lỗi, request fail rõ hoặc fail-open theo `RERANKER_FAIL_OPEN`; không fallback sang Hugging Face reranking API.

### 10. Conversational Memory Manager (Trí nhớ hội thoại lai)

Để tránh hiện tượng tràn ngữ cảnh (Context Bloat) và suy giảm độ tập trung của LLM khi cuộc hội thoại kéo dài:
- **Tóm tắt tịnh tiến (Incremental Summarization):** Chạy ngầm một model nhẹ (ví dụ `qwen2.5:1.5b`) thông qua `asyncio.create_task` ngay sau khi trả lời xong để nén các lượt chat cũ thành một đoạn tóm tắt ngắn gọn.
- **Trí nhớ lai (Sliding Window Context):** Khi tạo Prompt cho LLM sinh câu trả lời, hệ thống kết hợp `[Tóm tắt bối cảnh từ PostgreSQL]` + `[4 tin nhắn nguyên bản gần nhất]`.
Kỹ thuật này giúp tiết kiệm lượng lớn token API, giảm thiểu độ trễ (latency) mà người dùng vẫn cảm nhận mạch hội thoại được duy trì trơn tru.

---

## Tính năng

### Chatbot Pháp luật
- **Hỏi đáp pháp lý** bằng ngôn ngữ tự nhiên tiếng Việt.
- **Trích dẫn căn cứ pháp lý** — mỗi câu trả lời kèm nguồn điều khoản cụ thể.
- **Dẫn chiếu chéo tự động** — hệ thống tự tìm và đính kèm các điều luật liên quan.
- **Lọc theo lĩnh vực** — chọn chuyên ngành luật để tăng độ chính xác.

### Đa model AI
- **4 model LLM** lựa chọn: Gemma4-31B, Qwen3.5-9B, Llama3.1-8B, DeepSeek-R1-7B.
- **Chuyển đổi model** ngay trong giao diện — so sánh chất lượng câu trả lời.

### Giao diện hiện đại
- **UI chuyên nghiệp** — thiết kế tối giản, responsive, animations mượt.
- **Sidebar quản lý phiên chat** — tạo mới, chọn, xóa các cuộc hội thoại.
- **Lưu lịch sử đồng bộ** lên cơ sở dữ liệu PostgreSQL — mỗi lượt chat được lưu đủ `user/assistant` trước khi hoàn tất, hỗ trợ refresh an toàn và duy trì trí nhớ dài hạn.
- **Phím tắt** — Enter gửi, Shift+Enter xuống dòng.
- **Render Markdown** — câu trả lời hiển thị với format (heading, bold, list...).

### Pipeline dữ liệu & Ablation Study
- **Kiến trúc Modular** — Pipeline tách biệt thành 5 module: Embedding, Chunking, Search, Reranking, ContextBuilder.
- **Ablation Study** — Thay đổi thuật toán Search/Rerank linh hoạt chỉ bằng cấu hình `.env` mà không cần sửa code.
- **Embedding incremental** — chỉ embed file mới, bỏ qua file đã xử lý.
- **Dữ liệu lớn** — 5.756 điều khoản, 843 dẫn chiếu chéo từ 8 bộ luật quan trọng.

---

## Dữ liệu pháp luật

| # | Văn bản pháp luật | Số điều khoản | Dẫn chiếu |
|---|---|---|---|
| 1 | Luật Đất đai 2024 | 1.272 | 201 |
| 2 | Bộ luật Tố tụng Dân sự 2025 | 1.523 | 225 |
| 3 | Luật Bảo vệ Môi trường 2025 | 835 | 49 |
| 4 | Luật Nhà ở 2025 | 790 | 211 |
| 5 | Luật Xây dựng 2025 | 566 | 42 |
| 6 | Luật Kinh doanh BĐS 2025 | 349 | 53 |
| 7 | Luật Công chứng 2026 | 287 | 48 |
| 8 | Luật Tương trợ Tư pháp HS 2025 | 134 | 14 |
| | **Tổng cộng** | **5.756** | **843** |

### Schema dữ liệu

Mỗi file JSON trong `data/processed/` có cấu trúc:

```json
{
  "law_info": {
    "law_id": "LDD_2024",
    "law_name": "Luật Đất đai 2024",
    "publisher": "Quốc hội",
    "document_number": "45/VBHN/VPQH/2025",
    "effective_date": "...",
    "executive_summary": "Tóm tắt nội dung..."
  },
  "clauses": [
    {
      "id": "LDD_2024_D10_K1",
      "position": {
        "chapter": 1,
        "article": 10,
        "article_title": "Phân loại đất",
        "clause": 1
      },
      "content": "Nội dung điều khoản...",
      "cross_references": [
        {
          "target_id": "LDD_2024_D137",
          "anchor_text": "Điều 137",
          "description_summary": "..."
        }
      ],
      "tags": ["đất đai", "quyền sử dụng đất"]
    }
  ]
}
```

---

## Công nghệ

| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript 5.9 | App Router |
| **Styling** | TailwindCSS 4.1, tw-animate-css | Responsive |
| **UI** | lucide-react, react-markdown, motion | Icons + Markdown + Animation |
| **Backend** | FastAPI, Uvicorn, Python | Async API |
| **Database** | PostgreSQL, Qdrant | Persistent Storage |
| **LLM Framework** | LangChain (core, community, huggingface) | Orchestration |
| **Embedding** | Fine-tuned BGE-M3 local artifact | Multilingual, 1024 dims |
| **Vector DB** | Qdrant (Native Hybrid Search) | Cấu hình Named Vectors |
| **LLM Models** | Gemini Flash-Lite, Gemma, Qwen, Llama, DeepSeek | Browser-configured providers |

## Deployed Inference Setup

For deployed usage, users configure LLM providers from the browser configuration screen.
API keys entered by users are stored only in the current browser profile, then sent
to the backend per chat request. The backend uses those keys in memory for that
request and does not persist them.

Inference roles:

- `answer`: final legal answer generation.
- `rewriter`: query classification and rewrite before retrieval.
- `summarizer`: background memory summary updates.

Recommended first setup:

```text
Provider: Google AI Studio
Answer model: Gemini 3.1 Flash-Lite
Rewriter model: Gemini 3.1 Flash-Lite
Summarizer model: Gemini 3.1 Flash-Lite
```

Embeddings are not user-configurable at runtime. The retrieval stack uses the
server-managed fine-tuned local embedding model so queries use the same
embedding space as the indexed legal corpus. In `remote_first`, LLM provider
ordering is remote-first, but query embedding still comes from the local
fine-tuned artifact. Embedding failures are surfaced to the client and do not
fall back to Ollama, Hugging Face API, or stale FAISS results.

Deploy-safe reranking:

- `PIPELINE_RERANKING=cross_encoder`: local fine-tuned cross-encoder reranking
  from `RERANKER_MODEL`. It scores up to `RERANKER_MAX_CANDIDATES` retrieved
  documents per request.
- `PIPELINE_RERANKING=none`: disables reranking for rollback or latency
  troubleshooting.

Environment file roles:

- `.env`: local/server defaults, storage URLs, pipeline knobs, and optional
  server fallback API keys.
- `.env.example`: public template with all supported keys and safe defaults.
- Browser storage: per-user BYOK API keys and selected provider/model per role.

Rollback: ignore browser `inferenceConfig` payloads and rely on server-side
environment defaults such as `HUGGINGFACE_API_KEY`, `GOOGLE_API_KEY`,
`ENABLE_GOOGLE_FALLBACK`, and `INFERENCE_STRATEGY`.
