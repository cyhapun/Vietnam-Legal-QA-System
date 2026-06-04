# ⚖️ VietLaw AI — Hệ thống Hỏi đáp Pháp luật Việt Nam

Chatbot tra cứu pháp luật Việt Nam sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)**.  
Hệ thống truy xuất các điều khoản pháp luật liên quan từ cơ sở dữ liệu vector (FAISS), sau đó dùng LLM để sinh câu trả lời có trích dẫn căn cứ pháp lý chính xác.

> **Project môn học:** Introduction to Machine Learning

---

## 📑 Mục lục

- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Hướng dẫn cài đặt và chạy](#-hướng-dẫn-cài-đặt-và-chạy)
- [Kỹ thuật sử dụng](#-kỹ-thuật-sử-dụng)
- [Tính năng](#-tính-năng)
- [Dữ liệu pháp luật](#-dữ-liệu-pháp-luật)
- [Công nghệ](#-công-nghệ)

---

## 🏗️ Kiến trúc hệ thống

Hệ thống theo mô hình **Client-Server** với 2 thành phần chính giao tiếp qua REST API:

```
  NGƯỜI DÙNG
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 15)                   │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Sidebar  │  │ChatInterface │  │ ProviderSelector │   │
│  │(lịch sử) │  │  (giao diện) │  │  (chọn model)    │   │
│  └──────────┘  └──────┬───────┘  └──────────────────┘   │
│                       │                                  │
│               POST /api/chat                             │
│               ┌───────▼────────┐                         │
│               │ API Route Proxy│ ← Next.js API Route     │
│               └───────┬────────┘                         │
└───────────────────────┼─────────────────────────────────┘
                        │ HTTP POST (JSON)
┌───────────────────────▼─────────────────────────────────┐
│                 BACKEND (FastAPI + Python)                │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │ app/api/chat.py         → Xử lý request         │     │
│  │ app/services/rag.py     → Truy xuất + context    │     │
│  │ app/services/llm.py     → Gọi LLM + prompt      │     │
│  │ app/services/vectorstore.py → FAISS + Knowledge  │     │
│  │ app/config.py           → Cấu hình tập trung    │     │
│  └─────────────────────────────────────────────────┘     │
│       │                                                  │
│       │ HuggingFace Inference API                        │
│       ▼                                                  │
│  ┌─────────────────────────────────────────────┐         │
│  │ Embedding: BAAI/bge-m3 (multilingual)       │         │
│  │ LLM: Gemma4-31B / Qwen3.5 / Llama / DS-R1  │         │
│  └─────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

### Luồng xử lý chính

1. **User** nhập câu hỏi pháp lý → Frontend gửi `POST /api/chat`
2. **Next.js API Route** (proxy) chuyển tiếp request đến Backend FastAPI
3. **Backend** dùng FAISS retriever (MMR, k=6) tìm các điều khoản liên quan
4. Hàm `build_nested_context()` xây dựng **context 2 cấp** (dẫn chiếu đệ quy giữa các điều luật)
5. Context + lịch sử chat + câu hỏi → **System Prompt** → gọi LLM qua HuggingFace API
6. LLM sinh câu trả lời → trả về `{text, contextUsed}` → Frontend render Markdown + hiển thị căn cứ pháp lý

---

## 📁 Cấu trúc dự án

```
Vietnam-Legal-QA-System/
│
├── 📄 .env.example              # Template biến môi trường
├── 📄 .gitignore                # Git ignore rules
├── 📄 README.md                 # Tài liệu dự án (file này)
├── 📄 docker-compose.yml        # Docker Compose cho phát triển
│
├── 🐍 backend/                  # === BACKEND (Python + FastAPI) ===
│   ├── main.py                  # Entry point — chạy: python main.py
│   ├── rag_service.py           # Backward-compatible shim
│   ├── requirements.txt         # Dependencies Python
│   ├── embedded_files.json      # Tracking các file đã embedding
│   │
│   ├── app/                     # 📦 Package chính (modular)
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory + startup events
│   │   ├── config.py            # Cấu hình tập trung (paths, API keys, constants)
│   │   ├── models.py            # Pydantic schemas (ChatRequest, ChatResponse)
│   │   │
│   │   ├── api/                 # 🌐 API Layer
│   │   │   └── chat.py          # Router POST /chat — xử lý request/response
│   │   │
│   │   ├── services/            # ⚙️ Business Logic Layer
│   │   │   ├── llm.py           # Kết nối LLM (HuggingFace) + System Prompt
│   │   │   ├── rag.py           # RAG pipeline: retrieval + context building
│   │   │   └── vectorstore.py   # FAISS index + Knowledge Base + embedding
│   │   │
│   │   └── utils/               # 🔧 Utilities
│   │       └── logging.py       # Logging chuẩn (thay thế print())
│   │
│   ├── data/
│   │   ├── processed/           # 📚 8 file JSON dữ liệu pháp luật đã tiền xử lý
│   │   └── raw/                 # Dữ liệu thô (chưa có)
│   │
│   └── vietlaw_faiss_index/     # 🗄️ FAISS vector index (22.5 MB)
│       ├── index.faiss           # Vector data
│       └── index.pkl             # Metadata
│
├── ⚛️ frontend/                 # === FRONTEND (Next.js 15 + React 19) ===
│   ├── package.json             # Dependencies Node.js
│   ├── next.config.ts           # Cấu hình Next.js
│   ├── tsconfig.json            # Cấu hình TypeScript
│   ├── postcss.config.mjs       # PostCSS + TailwindCSS
│   │
│   ├── app/                     # 📱 Next.js App Router
│   │   ├── layout.tsx           # Root layout (metadata, global styles)
│   │   ├── page.tsx             # Trang chính — render ChatInterface
│   │   ├── globals.css          # CSS toàn cục + custom scrollbar
│   │   └── api/chat/
│   │       └── route.ts         # API Route Proxy → chuyển tiếp đến Backend
│   │
│   ├── components/              # 🧩 React Components
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx    # Giao diện chat chính (input, messages, toolbar)
│   │   │   ├── ChatMessage.tsx      # Hiển thị tin nhắn + căn cứ pháp lý
│   │   │   ├── ProviderSelector.tsx # Dropdown chọn model AI
│   │   │   └── Sidebar.tsx          # Sidebar quản lý phiên chat
│   │   └── ui/
│   │       └── LoadingSpinner.tsx   # Animation loading khi chờ LLM
│   │
│   ├── hooks/                   # 🪝 Custom React Hooks
│   │   ├── use-chat-sessions.ts # Quản lý sessions (CRUD, localStorage)
│   │   ├── use-click-outside.ts # Đóng dropdown khi click ngoài
│   │   └── use-mobile.ts       # Phát hiện thiết bị mobile
│   │
│   └── lib/                     # 📚 Shared Utilities
│       ├── types.ts             # TypeScript interfaces (Message, ChatSession, ...)
│       ├── constants.ts         # Hằng số (models, categories, storage keys)
│       └── utils.ts             # Hàm tiện ích (cn — class merging)
│
└── 📓 notebooks/                # === JUPYTER NOTEBOOKS ===
    └── embedding_model.ipynb    # Notebook thử nghiệm embedding model
```

### Giải thích thiết kế

| Layer | Vai trò | Files |
|---|---|---|
| **API Layer** | Nhận HTTP request, validate, trả response | `api/chat.py`, `models.py` |
| **Service Layer** | Business logic: RAG, LLM, Vector DB | `services/llm.py`, `rag.py`, `vectorstore.py` |
| **Config Layer** | Quản lý cấu hình, env, paths | `config.py` |
| **Utils Layer** | Tiện ích dùng chung | `utils/logging.py` |

> **Nguyên tắc:** Mỗi file **một nhiệm vụ duy nhất** (Single Responsibility). API layer không chứa business logic, service layer không biết về HTTP.

---

## 🚀 Hướng dẫn Cài đặt và Chạy

### Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| HuggingFace API key | Miễn phí — [Lấy tại đây](https://huggingface.co/settings/tokens) |

### Bước 1: Clone và cấu hình

```bash
# Clone repository
git clone https://github.com/cyhapun/Vietnam-Legal-QA-System.git
cd Vietnam-Legal-QA-System

# Tạo file biến môi trường từ template
cp .env.example .env

# Mở .env và điền API key của bạn
# HUGGINGFACE_API_KEY=hf_your_actual_key_here
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
# ✅ Server chạy tại: http://localhost:8000
```

> ⚠️ **Lưu ý quan trọng:** Phải chạy từ **thư mục `backend/`**, không phải từ thư mục root!

### Bước 3: Chạy Frontend (Terminal 2)

```bash
# Mở terminal MỚI, di chuyển vào thư mục frontend
cd frontend

# Cài đặt dependencies
npm install

# Khởi chạy dev server
npm run dev
# ✅ Mở trình duyệt tại: http://localhost:3000
```

### Chạy bằng Docker (Tùy chọn)

```bash
# Từ thư mục root project
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Lưu ý khi chạy

- **Backend phải chạy TRƯỚC Frontend** — Frontend proxy request đến Backend
- **FAISS index đã có sẵn** trong repo (22.5 MB) — không cần re-embed dữ liệu
- **Lần đầu khởi động** Backend sẽ nạp 8 file JSON vào RAM + tải FAISS index (~5-10 giây)
- Nếu muốn **re-embed dữ liệu**, xóa file `embedded_files.json` rồi restart server

---

## 🔬 Kỹ thuật sử dụng

### 1. RAG (Retrieval-Augmented Generation)

Kỹ thuật cốt lõi của hệ thống — **kết hợp truy xuất thông tin + sinh văn bản**:

```
Câu hỏi → [Retriever] → Điều khoản liên quan → [LLM] → Câu trả lời có trích dẫn
```

**Tại sao dùng RAG?** LLM đơn thuần có thể "bịa" thông tin pháp lý. RAG buộc LLM chỉ trả lời dựa trên dữ liệu thực tế được cung cấp, đảm bảo tính chính xác.

### 2. Vector Embedding + FAISS

- **Embedding model:** [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) — model đa ngôn ngữ, hỗ trợ tiếng Việt tốt, 1024 chiều
- **Vector DB:** FAISS (Facebook AI Similarity Search) — tìm kiếm tương đồng ngữ nghĩa cực nhanh
- **Chiến lược:** Cosine distance, batch size 32, retry 3 lần khi lỗi API
- Mỗi **điều khoản pháp luật = 1 vector** (chunking tự nhiên theo đơn vị pháp lý)

### 3. MMR Retrieval (Maximal Marginal Relevance)

Thay vì chỉ lấy top-K kết quả giống nhau nhất, MMR **cân bằng giữa độ liên quan và đa dạng**:

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `k` | 6 | Trả về 6 điều khoản liên quan nhất |
| `fetch_k` | 20 | Lấy 20 ứng viên ban đầu rồi chọn 6 |
| `lambda_mult` | 0.8 | 80% ưu tiên liên quan, 20% ưu tiên đa dạng |

### 4. Nested Context Building (Dẫn chiếu 2 cấp)

Tính năng nổi bật — xây dựng **context đệ quy** giúp LLM hiểu liên kết giữa các điều luật:

```
[Cấp 0] Điều khoản được retrieve → Hiển thị đầy đủ nội dung
   └── [Cấp 1] Dẫn chiếu từ Cấp 0 → Lấy toàn bộ content từ RAM
          └── [Cấp 2] Dẫn chiếu từ Cấp 1 → Chỉ lấy tóm tắt
```

**Ví dụ:** Điều 137 Luật Đất đai dẫn chiếu đến Điều 45 → hệ thống tự động lấy nội dung Điều 45 đưa vào context cho LLM.

### 5. Category-based Filtering

Lọc kết quả truy xuất theo **lĩnh vực pháp luật** để tăng độ chính xác:
- Kinh doanh, Đất đai, Bảo vệ môi trường, Tố tụng dân sự, Nhà ở
- Metadata `category` được gắn vào mỗi document khi embedding
- FAISS filter theo category trước khi tìm kiếm

### 6. Prompt Engineering

System prompt được thiết kế với **4 quy tắc bắt buộc** cho LLM:
1. **Trích dẫn rõ ràng:** Luôn nêu tên Luật, Chương, Điều, Khoản
2. **Xử lý dẫn chiếu:** Dùng nội dung dẫn chiếu để giải thích thuật ngữ
3. **Không suy đoán:** Chỉ trả lời dựa trên dữ liệu được cung cấp
4. **Ngôn ngữ:** Trả lời bằng tiếng Việt chuyên nghiệp, khách quan

### 7. Knowledge Base In-Memory

Toàn bộ 5.756 điều khoản được nạp vào **RAM** khi server khởi động → truy xuất dẫn chiếu chéo **không cần gọi API hay truy vấn DB**, đảm bảo tốc độ tối đa.

---

## ✨ Tính năng

### Chatbot Pháp luật
- 💬 **Hỏi đáp pháp lý** bằng ngôn ngữ tự nhiên tiếng Việt
- 📖 **Trích dẫn căn cứ pháp lý** — mỗi câu trả lời kèm nguồn điều khoản cụ thể
- 🔗 **Dẫn chiếu chéo tự động** — hệ thống tự tìm và đính kèm các điều luật liên quan
- 🗂️ **Lọc theo lĩnh vực** — chọn chuyên ngành luật để tăng độ chính xác

### Đa model AI
- 🤖 **4 model LLM** lựa chọn: Gemma4-31B, Qwen3.5-9B, Llama3.1-8B, DeepSeek-R1-7B
- 🔄 **Chuyển đổi model** ngay trong giao diện — so sánh chất lượng câu trả lời

### Giao diện hiện đại
- 🎨 **UI chuyên nghiệp** — thiết kế tối giản, responsive, animations mượt
- 📱 **Sidebar quản lý phiên chat** — tạo mới, chọn, xóa các cuộc hội thoại
- 💾 **Lưu lịch sử tự động** vào localStorage — không mất khi tải lại trang
- ⌨️ **Phím tắt** — Enter gửi, Shift+Enter xuống dòng
- 📜 **Render Markdown** — câu trả lời hiển thị với format đẹp (heading, bold, list...)

### Pipeline dữ liệu
- ⚡ **Embedding incremental** — chỉ embed file mới, bỏ qua file đã xử lý
- 🔄 **Tự động retry** — retry 3 lần với backoff khi API lỗi
- 📊 **5.756 điều khoản**, **843 dẫn chiếu chéo** từ 8 bộ luật quan trọng

---

## 📊 Dữ liệu pháp luật

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

## 🛠️ Công nghệ

| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript 5.9 | App Router |
| **Styling** | TailwindCSS 4.1, tw-animate-css | Responsive |
| **UI** | lucide-react, react-markdown, motion | Icons + Markdown + Animation |
| **Backend** | FastAPI, Uvicorn, Python | Async API |
| **LLM Framework** | LangChain (core, community, huggingface) | Orchestration |
| **Embedding** | BAAI/bge-m3 qua HuggingFace API | Multilingual, 1024 dims |
| **Vector DB** | FAISS (faiss-cpu) | In-memory, Cosine distance |
| **LLM Models** | Gemma4-31B, Qwen3.5-9B, Llama3.1-8B, DeepSeek-R1-7B | HF Inference API |
