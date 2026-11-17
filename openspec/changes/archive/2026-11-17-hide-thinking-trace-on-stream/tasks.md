# Tasks: Hide Thinking Trace on Answer Streaming

## 1. Cập Nhật Điều Kiện Hiển Thị Tiến Trình
- [x] 1.1 Cập nhật `frontend/components/chat/ChatMessage.tsx`:
  - Bổ sung điều kiện kiểm tra `!message.content?.trim()` trước khi render `<ChatProcessingTrace />`.
  - Đảm bảo khi `message.content` đã có token/nội dung chữ thì tiến trình lập tức unmount.

## 2. Kiểm Thử & Xác Minh
- [x] 2.1 Cập nhật `frontend/scripts/verify-chat-ux.mjs`:
  - Thêm assertion xác nhận `ChatMessage.tsx` chỉ hiển thị `ChatProcessingTrace` khi `!message.content?.trim()`.
- [x] 2.2 Chạy bộ kiểm thử UX frontend: `npm run verify:chat-ux`.
- [x] 2.3 Chạy kiểm tra TypeScript và Build frontend: `cd frontend && npx tsc --noEmit && npm run build`.
- [x] 2.4 Đảm bảo toàn bộ 31 bài test backend vẫn pass 100%: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/`.
