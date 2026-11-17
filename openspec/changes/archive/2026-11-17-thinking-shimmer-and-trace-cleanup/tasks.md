# Tasks: Shimmering Thinking Text & Trace Cleanup

## 1. CSS & Hiệu Ứng Shimmering Text
- [x] 1.1 Cập nhật `frontend/app/globals.css`:
  - Định nghĩa `@keyframes thinking-shimmer` tạo hiệu ứng chuyển động gradient ngang.
  - Thêm class `.animate-thinking-shimmer` với gradient tương thích hoàn hảo cả Light mode và Dark mode.

## 2. Tinh Chỉnh Component & Xóa Bỏ Bảng Quá Trình
- [x] 2.1 Cập nhật `frontend/components/chat/ChatProcessingTrace.tsx`:
  - Loại bỏ hoàn toàn cấu trúc pill viền/background bo tròn, nút toggle (`Xem quá trình`), icon chevron và danh sách timeline (`ol/li`).
  - Khi `stage === 'completed'` hoặc `stage === 'idle'`: Trả về `null` hoàn toàn để xóa hẳn tiến trình khi câu trả lời kết thúc.
  - Khi active (`analyzing`, `searching`, `selecting`, `generating`): Render dòng text thuần túy thanh thoát kết hợp class `.animate-thinking-shimmer` và icon `Sparkles`.
  - Khi `cancelled` hoặc `error`: Render thông báo trạng thái ngắn gọn tối giản.
- [x] 2.2 Cập nhật `frontend/components/chat/ChatMessage.tsx`:
  - Xóa bỏ state `isProcessCollapsed` không còn sử dụng.
  - Truyền `stage={message.processingStage}` trực tiếp vào `ChatProcessingTrace`.

## 3. Cập Nhật Kiểm Thử & Xác Minh Toàn Diện
- [x] 3.1 Cập nhật kịch bản kiểm thử frontend `frontend/scripts/verify-chat-ux.mjs`:
  - Đồng bộ các nhãn thinking text mới (`Đang phân tích câu hỏi...`, `Đang tra cứu căn cứ pháp lý...`).
  - Kiểm tra việc không còn render pill/bảng thừa (`Tra cứu hoàn tất`, `Xem quá trình`) sau khi hoàn thành.
- [x] 3.2 Chạy bộ kiểm thử UX frontend: `npm run verify:chat-ux`.
- [x] 3.3 Chạy kiểm tra biên dịch frontend: `cd frontend && npx tsc --noEmit && npm run build`.
- [x] 3.4 Đảm bảo toàn bộ 31 bài test backend vẫn pass 100%: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/`.
