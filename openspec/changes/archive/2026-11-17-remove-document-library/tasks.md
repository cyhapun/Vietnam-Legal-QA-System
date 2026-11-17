# Tasks: Remove Document Library Module

## 1. Gỡ Bỏ Nút "Kho Tài Liệu" Trên Sidebar
- [x] 1.1 Cập nhật `frontend/components/chat/Sidebar.tsx`:
  - Xóa bỏ nút `<Link href="/docs">...Kho Tài Liệu</Link>`.
  - Xóa bỏ import `LibraryBig` và `Link` (nếu không còn sử dụng).

## 2. Xóa Bỏ Trang, Component và API Proxy Docs
- [x] 2.1 Xóa trang `frontend/app/docs/page.tsx` và thư mục `frontend/app/docs/`.
- [x] 2.2 Xóa các component `frontend/components/docs/ChunkViewer.tsx`, `DocumentList.tsx`, `UploadModal.tsx` và thư mục `frontend/components/docs/`.
- [x] 2.3 Xóa proxy route `frontend/app/api/documents/[[...slug]]/route.ts` và thư mục `frontend/app/api/documents/`.

## 3. Cấu Hình Chuyển Hướng An Toàn & Cập Nhật Kiểm Thử
- [x] 3.1 Cập nhật `frontend/next.config.ts`: thêm `redirects()` cho `/docs` chuyển hướng về `/`.
- [x] 3.2 Cập nhật kịch bản kiểm thử UX `frontend/scripts/verify-chat-ux.mjs`: xác nhận không còn nhãn hoặc liên kết "Kho Tài Liệu" trong `Sidebar.tsx`.

## 4. Kiểm Thử & Xác Minh Toàn Diện
- [x] 4.1 Chạy kịch bản kiểm thử UX: `npm run verify:chat-ux`.
- [x] 4.2 Chạy TypeScript check: `cd frontend && npx tsc --noEmit`.
- [x] 4.3 Chạy production build: `cd frontend && npm run build`.
- [x] 4.4 Kiểm tra redirect HTTP `/docs` qua curl: `curl -I http://localhost:3000/docs`.
- [x] 4.5 Chạy bộ kiểm thử hồi quy backend: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/`.
