# ⚖️ VietLaw AI — Hệ thống Hỏi đáp Pháp luật Việt Nam

Chatbot tra cứu pháp luật Việt Nam sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)**.  
Hệ thống truy xuất các điều khoản pháp luật liên quan từ cơ sở dữ liệu vector, sau đó dùng LLM để sinh câu trả lời có trích dẫn căn cứ pháp lý.

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 15)               │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ Sidebar  │ │ChatInterface │ │ ProviderSelector │ │
│  └──────────┘ └──────┬───────┘ └──────────────────┘ │
│                      │ POST /api/chat                │
│              ┌───────▼────────┐                      │
│              │ API Route Proxy│                      │
│              └───────┬────────┘                      │
└──────────────────────┼──────────────────────────────┘
                       │ HTTP POST
┌──────────────────────▼──────────────────────────────┐
│                BACKEND (FastAPI + Python)             │
│  ┌────────────────────────────────────────────────┐  │
│  │ app/                                           │  │
│  │ ├── api/chat.py     → Router                   │  │
│  │ ├── services/llm.py → LLM + Prompt             │  │
│  │ ├── services/rag.py → Retrieval + Context       │  │
│  │ └── services/vectorstore.py → FAISS + KB        │  │
│  └────────────────────────────────────────────────┘  │
│       │ HuggingFace Inference API                    │
│       ▼                                              │
│  ┌─────────────────────────────────────────────┐     │
│  │ LLM: Gemma4 / Qwen3.5 / Llama3.1 / DeepSeek│     │
│  │ Embedding: BAAI/bge-m3                       │     │
│  └─────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

## 📊 Dữ liệu

| Văn bản pháp luật | Số điều khoản |
|---|---|
| Luật Đất đai 2024 | 1.272 |
| Bộ luật Tố tụng Dân sự 2025 | 1.523 |
| Luật Bảo vệ Môi trường 2025 | 835 |
| Luật Nhà ở 2025 | 790 |
| Luật Xây dựng 2025 | 566 |
| Luật Kinh doanh BĐS 2025 | 349 |
| Luật Công chứng 2026 | 287 |
| Luật Tương trợ Tư pháp HS 2025 | 134 |
| **Tổng** | **5.756** |

## 🚀 Hướng dẫn Cài đặt

### Yêu cầu
- Python 3.10+
- Node.js 18+
- HuggingFace API key ([Lấy tại đây](https://huggingface.co/settings/tokens))

### Các bước

```bash
# 1. Clone repo
git clone https://github.com/cyhapun/Vietnam-Legal-QA-System.git
cd Vietnam-Legal-QA-System

# 2. Cấu hình biến môi trường
cp .env.example .env
# Mở .env và điền HUGGINGFACE_API_KEY của bạn

# 3. Chạy Backend
cd backend
pip install -r requirements.txt
python main.py
# Server chạy tại http://localhost:8000

# 4. Chạy Frontend (terminal khác)
cd frontend
npm install
npm run dev
# Mở http://localhost:3000
```

> **Lưu ý:** Backend phải chạy **trước** Frontend. FAISS index đã có sẵn trong repo — không cần re-embed.

## 🛠️ Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, TailwindCSS 4 |
| Backend | FastAPI, LangChain, FAISS |
| Embedding | BAAI/bge-m3 (HuggingFace API) |
| LLM | Gemma4-31B, Qwen3.5-9B, Llama3.1-8B, DeepSeek-R1-7B |

## 📁 Cấu trúc thư mục

```
├── backend/
│   ├── app/                    # Package chính
│   │   ├── api/chat.py         # API endpoint
│   │   ├── services/           # Business logic
│   │   │   ├── llm.py          # LLM + prompt
│   │   │   ├── rag.py          # Retrieval + context
│   │   │   └── vectorstore.py  # FAISS + knowledge base
│   │   ├── utils/logging.py    # Logging chuẩn
│   │   ├── config.py           # Cấu hình tập trung
│   │   └── models.py           # Pydantic schemas
│   ├── data/processed/         # Dữ liệu pháp luật JSON
│   ├── vietlaw_faiss_index/    # FAISS vector index
│   ├── main.py                 # Entry point
│   └── requirements.txt
├── frontend/
│   ├── app/                    # Next.js App Router
│   ├── components/
│   │   ├── chat/               # Chat UI components
│   │   └── ui/                 # Shared UI components
│   ├── hooks/                  # Custom React hooks
│   └── lib/                    # Types, constants, utils
└── notebooks/                  # Jupyter notebooks
```

## 👥 Tác giả

Project môn học **Introduction to Machine Learning**
