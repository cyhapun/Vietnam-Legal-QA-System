# Proposal: Fix Vercel Services Framework Configuration

## 1. Problem Statement
Khi triển khai (deploy) dự án lên Vercel từ branch `feat/refine-rag-pipeline`, quá trình build của Vercel CLI (v65.15.0) bị dừng lại với lỗi:
```text
WARNING! The 'experimentalServices' property is deprecated. Migrate to 'services'.
Error: [MULTIPLE_FRAMEWORKS_SERVICE] Multiple frameworks detected in backend/: FastAPI, Container. Specify "framework" explicitly in services.
```

### Nguyên nhân:
1. **Thuộc tính lỗi thời (Deprecated Property):** `vercel.json` đang sử dụng `experimentalServices`, vốn đã bị Vercel thay thế bằng cấu hình chính thức `services`.
2. **Xung đột nhận diện framework:** Thư mục `backend/` chứa cả `backend/Dockerfile` (dùng cho môi trường Docker Compose cục bộ) và các file ứng dụng Python FastAPI (`backend/main.py`, `requirements.txt`).
3. **Thiếu khai báo tường minh:** Service `backend` trong `vercel.json` chỉ có `entrypoint: "backend"` và `routePrefix: "/_/backend"`, không có thuộc tính `"framework"`. Do đó, cơ chế auto-detection của Vercel phát hiện ra cả 2 framework `FastAPI` và `Container`, dẫn đến xung đột `[MULTIPLE_FRAMEWORKS_SERVICE]`.

## 2. Proposed Changes
1. **Chuyển đổi `experimentalServices` thành `services`:** Cập nhật `vercel.json` theo đúng tiêu chuẩn hiện hành của Vercel.
2. **Khai báo tường minh `"framework": "fastapi"` cho backend:** Bổ sung `"framework": "fastapi"` vào cấu hình service `backend` trong `vercel.json`.
3. **Giữ nguyên các biến môi trường serverless:** Đảm bảo toàn bộ cấu hình môi trường runtime `serverless` (HuggingFace API, PIPELINE_RERANKING, v.v.) hoạt động trơn tru.

## 3. Goals & Non-Goals

### Goals
- Loại bỏ hoàn toàn cảnh báo `The 'experimentalServices' property is deprecated`.
- Khắc phục triệt để lỗi `[MULTIPLE_FRAMEWORKS_SERVICE]` trong quá trình build trên Vercel.
- Đảm bảo Vercel nhận diện chính xác service `backend` là `fastapi` serverless function và service `frontend` là `nextjs`.
- Xác minh tính hợp lệ của cú pháp JSON trong `vercel.json`.

### Non-Goals
- Không thay đổi mã nguồn logic bên trong `backend/` hoặc `frontend/`.
- Không xóa bỏ `backend/Dockerfile` vì vẫn cần thiết cho việc chạy Docker Compose trên máy local.
