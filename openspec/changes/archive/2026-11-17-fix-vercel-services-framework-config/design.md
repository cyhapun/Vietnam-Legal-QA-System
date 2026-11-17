# Design: Fix Vercel Services Framework Configuration

## 1. Context & Architecture

VietLaw AI triển khai kiến trúc đa dịch vụ (Multi-service) trên Vercel:
- **`frontend`**: Next.js App Router, phục vụ giao diện người dùng và định tuyến tại `/`.
- **`backend`**: FastAPI Python ASGI application, phục vụ các API truy vấn RAG và định tuyến nội bộ tại `/_/backend`.

```
                         Vercel Edge / Domain Router
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
       ┌──────────────────────┐              ┌──────────────────────┐
       │   service: frontend  │              │   service: backend   │
       │ (framework: nextjs)  │              │ (framework: fastapi) │
       ├──────────────────────┤              ├──────────────────────┤
       │ • Route: /           │              │ • Route: /_/backend  │
       │ • Entrypoint:        │              │ • Entrypoint:        │
       │   frontend           │              │   backend            │
       └──────────────────────┘              └──────────────────────┘
```

---

## 2. Configuration Specification (`vercel.json`)

Cấu hình mới của file `vercel.json`:
```json
{
  "env": {
    "RUNTIME_PROFILE": "serverless",
    "CHAT_STORAGE_MODE": "browser",
    "NEXT_PUBLIC_CHAT_STORAGE_MODE": "browser",
    "HUGGINGFACE_EMBEDDING_MODE": "api",
    "HUGGINGFACE_EMBEDDING_MODEL": "BAAI/bge-m3",
    "PIPELINE_RERANKING": "embedding_similarity",
    "LOCAL_MODELS_PRELOAD_ENABLED": "false",
    "LOCAL_MODELS_WARMUP_ENABLED": "false"
  },
  "services": {
    "frontend": {
      "entrypoint": "frontend",
      "routePrefix": "/",
      "framework": "nextjs"
    },
    "backend": {
      "entrypoint": "backend",
      "routePrefix": "/_/backend",
      "framework": "fastapi"
    }
  }
}
```

### Chi tiết thay đổi:
1. `experimentalServices` ➔ `services`: Tuân thủ phiên bản Vercel CLI 65.x+ mới nhất.
2. `services.backend.framework`: Đặt tường minh là `"fastapi"` để chỉ đạo Vercel build qua runtime Python Serverless, ngăn chặn detector quét `Dockerfile` và gắn nhãn nhầm là `Container`.

---

## 3. Verification Strategy

1. **Kiểm tra cú pháp JSON:** Chạy `node -e "JSON.parse(fs.readFileSync('vercel.json'))"` để bảo đảm file JSON hợp lệ 100%.
2. **Kiểm tra cấu trúc services:** Xác nhận `services.backend.framework === 'fastapi'` và `services.frontend.framework === 'nextjs'`.
3. **Kiểm tra hồi quy Frontend & Backend:** Chạy `npm run verify:chat-ux` và `pytest tests/` để đảm bảo không có tác động tiêu cực nào đến hệ thống.
