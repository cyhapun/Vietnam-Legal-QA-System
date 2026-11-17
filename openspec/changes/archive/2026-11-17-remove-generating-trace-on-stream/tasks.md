# Tasks: Remove Generating Trace on Stream

## 1. Cập Nhật Logic Chặn Kép (Dual Guard)
- [x] 1.1 Cập nhật `frontend/components/chat/ChatProcessingTrace.tsx`:
  - Thêm `stage === 'generating'` vào điều kiện trả về `null` ngay đầu component.
  - Xóa bỏ hoàn toàn nhánh `'generating'` và chuỗi `"Đang tổng hợp câu trả lời..."`.
- [x] 1.2 Cập nhật `frontend/components/chat/ChatMessage.tsx`:
  - Bổ sung điều kiện chặn `message.processingStage !== 'generating'` khi render `<ChatProcessingTrace />`.

## 2. Kiểm Thử & Xác Minh
- [x] 2.1 Cập nhật kịch bản kiểm thử frontend `frontend/scripts/verify-chat-ux.mjs`:
  - Bỏ nhãn `"Đang tổng hợp câu trả lời"` khỏi danh sách bắt buộc của `ChatProcessingTrace`.
  - Thêm assertion kiểm chứng `stage === 'generating'` trả về `null` và không có chuỗi `"Đang tổng hợp"` trong component.
- [x] 2.2 Chạy bộ kiểm thử UX frontend: `npm run verify:chat-ux`.
- [x] 2.3 Chạy kiểm tra TypeScript và Build frontend: `cd frontend && npx tsc --noEmit && npm run build`.
- [x] 2.4 Đảm bảo toàn bộ 31 bài test backend vẫn pass 100%: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/`.
