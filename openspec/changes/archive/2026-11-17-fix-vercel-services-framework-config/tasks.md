# Tasks: Fix Vercel Services Framework Configuration

## 1. Cập Nhật Cấu Hình Vercel (`vercel.json`)
- [x] 1.1 Thay thế `experimentalServices` bằng `services` trong `vercel.json`.
- [x] 1.2 Bổ sung `"framework": "fastapi"` vào cấu hình của service `backend` trong `vercel.json`.

## 2. Kiểm Thử & Xác Minh
- [x] 2.1 Kiểm tra cú pháp và cấu trúc JSON của `vercel.json`: đảm bảo hợp lệ và có đầy đủ trường `framework` cho cả `frontend` và `backend`.
- [x] 2.2 Chạy bộ kiểm thử UX frontend: `npm run verify:chat-ux`.
- [x] 2.3 Chạy kiểm tra TypeScript và build frontend: `cd frontend && npx tsc --noEmit && npm run build`.
- [x] 2.4 Chạy bộ kiểm thử hồi quy backend: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/`.
