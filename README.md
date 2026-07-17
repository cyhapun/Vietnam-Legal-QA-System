# VietLaw AI - Hệ thống Hỏi đáp Pháp luật Việt Nam

Chatbot tra cứu pháp luật Việt Nam sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)**.
Hệ thống tách dữ liệu pháp luật thành các điều khoản, lập chỉ mục dense/sparse trong Qdrant,
truy xuất các căn cứ liên quan và dùng LLM để sinh câu trả lời tiếng Việt có citation.

Luồng triển khai chính dùng **PostgreSQL + Qdrant**. FAISS vẫn được hỗ trợ cho chạy local hoặc
làm fallback khi Qdrant không sẵn sàng. Các thành phần retrieval, reranking, query rewriting,
context building và inference được ghép theo cấu hình để phục vụ ablation study.

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
- [Fine-tuning và đánh giá](#fine-tuning-và-đánh-giá)
- [Công nghệ](#công-nghệ)

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
│       │ HuggingFace Inference API                       │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────┐        │
│  │ Embedding: BAAI/bge-m3 (multilingual)       │        │
│  │ LLM: Gemini / Gemma / Qwen / Llama / DeepSeek │       │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Luồng xử lý chính

1. Người dùng nhập câu hỏi; `frontend/app/api/chat/route.ts` proxy request đến FastAPI.
2. Mặc định frontend dùng `POST /chat/stream` và nhận Server-Sent Events; có thể tắt streaming để gọi `POST /chat`.
3. Backend lấy summary của session và một cửa sổ lịch sử chat gần nhất.
4. Query Rewriter tùy chọn phân loại `legal/chitchat`, chuẩn hóa câu hỏi và tách sub-query.
5. Semantic Cache kiểm tra câu hỏi tương tự; cache hit được trả về ngay.
6. RAG Pipeline thực hiện search, loại trùng, reranking và dựng context dẫn chiếu hai cấp.
7. Context + memory + câu hỏi được đưa vào prompt, sau đó gọi LLM theo role `answer`.
8. Backend lọc citation, stream câu trả lời hoặc trả `{text, contextUsed}`.
9. Cặp `user/assistant` được lưu vào PostgreSQL trước khi trả response/emit SSE `done`; summary được cập nhật nền.

### Hai pipeline dữ liệu

```text
INGESTION
data/processed/*.json
  → load Knowledge Base
  → ClauseChunker
  → dense embedding (BAAI/bge-m3) + sparse BM25 vector
  → PostgreSQL (law/clause metadata, content)
  → Qdrant (text-dense, text-sparse, payload)

ONLINE QA
question
  → rewrite/route + semantic cache
  → Qdrant hybrid search + RRF (hoặc FAISS fallback)
  → deduplicate → optional reranking
  → NestedContextBuilder + token budget
  → LLM → citation filtering → stream/JSON response
```

Ingestion không nên chạy lại ở mỗi lần khởi động. Với Docker, backend đặt
`DISABLE_AUTO_INGEST=true` và việc nạp dữ liệu được thực hiện bằng service `ingest`.

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
│   │   ├── processed/           # 9 JSON: 8 bộ luật chính + dữ liệu mẫu
│   │   └── raw/                 # Dữ liệu thô (chưa có)
│   │
│   └── vietlaw_faiss_index/     # FAISS index local/fallback (nếu có)
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
├── fine-tuning/                 # Fine-tune embedding/reranker và artifact đánh giá
│   ├── embedding/notebooks/
│   └── reranking/notebooks/
└── backend/evaluation/          # Chuẩn bị dataset và đánh giá Ragas
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
| HuggingFace API key | Miễn phí — [Lấy tại đây](https://huggingface.co/settings/tokens) |

`requirements.txt` hỗ trợ embedding qua HuggingFace API. Nếu muốn chạy embedding
local với `HUGGINGFACE_EMBEDDING_MODE=local`, cần cài thêm `sentence-transformers`
và PyTorch; Dockerfile đã cài sẵn các gói này.

### Bước 1: Clone và cấu hình

```bash
# Clone repository
git clone https://github.com/cyhapun/Vietnam-Legal-QA-System.git
cd Vietnam-Legal-QA-System

# Tạo file biến môi trường từ template
cp .env.example .env

# `.env` chứa cấu hình server, storage và pipeline. API key/model của người dùng
# được cấu hình trong giao diện web và truyền theo từng request.
#
# Cấu hình mặc định nên giữ:
# EMBEDDING_PROVIDER=huggingface
# HUGGINGFACE_EMBEDDING_MODEL=BAAI/bge-m3
# HUGGINGFACE_EMBEDDING_MODE=api
# STORAGE_BACKEND=qdrant_postgres
#
# Khi chạy backend trực tiếp trên host, dùng localhost cho PostgreSQL/Qdrant.
# Khi chạy bằng Docker Compose, đổi host thành tên service:
# POSTGRES_DSN=postgresql://postgres:postgres@postgres:5432/vietlaw
# QDRANT_URL=http://qdrant:6333
#
# `remote_first` chỉ dùng remote providers; `local_first` dùng Ollama trước.
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

### Bước 2a: Chạy với PostgreSQL + Qdrant

```bash
# Từ thư mục root project
docker compose up -d postgres qdrant

# Trong .env, dùng storage backend database-backed và hostname của host
# nếu chạy script ingest từ máy local:
# STORAGE_BACKEND=qdrant_postgres
# POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/vietlaw
# QDRANT_URL=http://localhost:6333

# Chạy từ thư mục backend
cd backend
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

### Chạy toàn bộ bằng Docker

```bash
# Từ thư mục root project; backend cố ý không auto-ingest
docker compose up --build -d

# Nạp dữ liệu sau khi PostgreSQL và Qdrant đã sẵn sàng
docker compose --profile tools run --rm ingest

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

Khi chạy toàn bộ bằng Docker, `.env` phải dùng hostname nội bộ:

```dotenv
POSTGRES_DSN=postgresql://postgres:postgres@postgres:5432/vietlaw
QDRANT_URL=http://qdrant:6333
```

### Lưu ý khi chạy

- **Backend phải chạy TRƯỚC Frontend** — Frontend proxy request đến Backend.
- Khi dùng FAISS, backend tải index local và dùng Knowledge Base trong RAM để dựng context.
- Khi dùng `qdrant_postgres`, startup tạo schema PostgreSQL và collection Qdrant nếu cần.
- Docker đặt `DISABLE_AUTO_INGEST=true`; native execution có thể bật auto-ingest bằng `false`.
- Để nạp dữ liệu ban đầu hoặc re-embed dữ liệu mới, chạy `python scripts/ingest_to_storage.py`
  từ `backend/`, hoặc chạy service `ingest` trong Docker Compose.
- Nếu Qdrant không truy cập được, `QdrantSearcher` cố gắng fallback sang FAISS; embedding
  HuggingFace lỗi xác thực/server được trả về rõ ràng để tránh truy vấn bằng vector space khác.

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
- **Dense Vector Search**: Semantic search qua model đa ngôn ngữ `BAAI/bge-m3` (1024 chiều).
- **Sparse Vector Search (BM25)**: Tìm kiếm từ khóa chính xác (Exact Keyword Match) thông qua thuật toán sinh vector thưa tự xây dựng cho tiếng Việt.
- **Reciprocal Rank Fusion (RRF)**: Qdrant nhận các truy vấn dense/sparse qua nhiều khối `prefetch`; backend dùng `query_batch_points` và hợp nhất thứ hạng bằng RRF để tương thích với các phiên bản Qdrant khác nhau.
- *(Dự phòng: Vẫn hỗ trợ FAISS cục bộ cho hệ thống không có Qdrant)*.

### 3. Cross-Encoder Reranking

Sau bước Search, kết quả có thể được xếp hạng lại (Reranking) để tăng độ chính xác:
- **CrossEncoderReranker**: Dùng model `BAAI/bge-reranker-v2-m3` để đánh giá chi tiết (joint encoding) giữa Query và Document.
- Có thể bật/tắt qua `PIPELINE_RERANKING=none|embedding_similarity|cross_encoder`. Trong `remote_first`, `cross_encoder` tự chuyển sang embedding-similarity để tương thích với HuggingFace Inference Providers.

### 4. MMR Retrieval (Maximal Marginal Relevance)

Thay vì chỉ lấy top-K kết quả giống nhau nhất, MMR **cân bằng giữa độ liên quan và đa dạng**:

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `k` | 60 | Số ứng viên tối đa lấy từ API trước các bước lọc/rerank |
| `fetch_k` | `max(20, k)` | Số ứng viên FAISS dùng cho MMR |
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
- **Embedding Layer**: retrieval triển khai cố định trên HuggingFace `BAAI/bge-m3` để đồng nhất với vector đã index. Nếu HuggingFace embedding trả `401` hoặc `500`, API trả lỗi rõ cho người dùng thay vì âm thầm dùng local hoặc trả kết quả rỗng.
- **Reranking Layer**: `PIPELINE_RERANKING=embedding_similarity` dùng HuggingFace `BAAI/bge-m3` remote để cosine rerank candidate docs trên deploy. Nếu cấu hình `cross_encoder` trong `remote_first`, backend tự chuyển sang embedding-similarity reranker vì HuggingFace Inference Providers không expose ổn định query/passage pair cho `BAAI/bge-reranker-v2-m3`.

### 10. Conversational Memory Manager (Trí nhớ hội thoại lai)

Để tránh hiện tượng tràn ngữ cảnh (Context Bloat) và suy giảm độ tập trung của LLM khi cuộc hội thoại kéo dài:
- **Tóm tắt tịnh tiến (Incremental Summarization):** Chạy ngầm một model nhẹ (ví dụ `qwen2.5:1.5b`) thông qua `asyncio.create_task` ngay sau khi trả lời xong để nén các lượt chat cũ thành một đoạn tóm tắt ngắn gọn.
- **Trí nhớ lai (Sliding Window Context):** Khi tạo Prompt cho LLM sinh câu trả lời, hệ thống kết hợp `[Tóm tắt bối cảnh từ PostgreSQL]` + `[4 tin nhắn nguyên bản gần nhất]`.
Kỹ thuật này giúp tiết kiệm lượng lớn token API, giảm thiểu độ trễ (latency) mà người dùng vẫn cảm nhận mạch hội thoại được duy trì trơn tru.

---

## Fine-tuning và đánh giá

Thư mục `fine-tuning/` chứa các notebook cho hai hướng thử nghiệm:

- `embedding/`: sinh dữ liệu query–điều khoản, fine-tune bi-encoder và so sánh embedding.
- `reranking/`: tạo hard negatives, fine-tune cross-encoder và đánh giá reranker.

Đánh giá end-to-end nằm trong `backend/evaluation/`. Dataset được chuẩn bị từ
`VLSP2025-LegalSML`, sau đó script gọi API `/chat` và tính các metric Ragas:
`context_precision`, `context_recall`, `faithfulness` và `answer_relevancy`.

```bash
cd backend
pip install -r evaluation/requirements.txt
python evaluation/prepare_dataset.py
python evaluation/evaluate.py
```

Backend phải đang chạy tại `http://localhost:8000`; kết quả chi tiết được ghi vào
`backend/evaluation/results.csv`.

---

## Tính năng

### Chatbot Pháp luật
- **Hỏi đáp pháp lý** bằng ngôn ngữ tự nhiên tiếng Việt.
- **Trích dẫn căn cứ pháp lý** — mỗi câu trả lời kèm nguồn điều khoản cụ thể.
- **Dẫn chiếu chéo tự động** — hệ thống tự tìm và đính kèm các điều luật liên quan.
- **Lọc theo lĩnh vực** — chọn chuyên ngành luật để tăng độ chính xác.

### Đa model AI
- **Nhiều provider/model**: Google AI Studio, HuggingFace Router và Ollama; danh sách model hợp lệ được kiểm soát trong `provider_registry.py`.
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
- **Ingestion idempotent** — bỏ qua khi database đã có đủ điều khoản; chạy lại script khi thêm/sửa dữ liệu để upsert và invalidate cache.
- **Dữ liệu** — 5.756 điều khoản và 843 dẫn chiếu chéo từ 8 bộ luật chính; thư mục hiện có thêm một JSON mẫu kiểm thử.

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
| **Embedding** | HuggingFace BAAI/bge-m3 | Multilingual, 1024 dims |
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
Answer model: Gemini 2.5 Flash-Lite
Rewriter model: Gemini 2.5 Flash-Lite
Summarizer model: Gemini 2.5 Flash-Lite
```

Embeddings are not user-configurable at runtime. The deployed retrieval stack
stays fixed to HuggingFace `BAAI/bge-m3` so queries use the same embedding space
as the indexed legal corpus. In `remote_first`, embedding failures are surfaced
to the client: invalid HuggingFace credentials return an authentication error,
and HuggingFace server failures return an embedding-service error. The deployed
path does not fall back to local Ollama.

Deploy-safe reranking:

- `PIPELINE_RERANKING=embedding_similarity`: remote-only reranking using
  HuggingFace `BAAI/bge-m3` feature extraction and cosine similarity. It scores
  up to `RERANKER_MAX_CANDIDATES` retrieved documents per request to keep deploy
  latency bounded.
- `PIPELINE_RERANKING=cross_encoder`: kept for local/experimental use. In
  `remote_first`, it resolves to embedding-similarity reranking to avoid the
  unsupported HuggingFace text-classification query/passage pair format.

Environment file roles:

- `.env`: local/server defaults, storage URLs, pipeline knobs, and optional
  server fallback API keys.
- `.env.example`: public template with all supported keys and safe defaults.
- Browser storage: per-user BYOK API keys and selected provider/model per role.

Rollback: ignore browser `inferenceConfig` payloads and rely on server-side
environment defaults such as `HUGGINGFACE_API_KEY`, `GOOGLE_API_KEY`,
`ENABLE_GOOGLE_FALLBACK`, and `INFERENCE_STRATEGY`.
