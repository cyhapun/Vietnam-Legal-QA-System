# Tasks: Chat Actions Refinement & True Answer Regeneration

## 1. Tinh Chỉnh Giao Diện Thanh Công Cụ (Icon-Only Toolbar)
- [x] 1.1 Cập nhật `frontend/components/chat/ChatMessage.tsx`:
  - Chuyển đổi toàn bộ nút thao tác ở chân câu trả lời AI sang dạng Icon-Only: Sao chép (`<Copy>`), Tạo lại (`<RotateCcw>`), Hữu ích (`<ThumbsUp>`), Báo cáo (`<ThumbsDown>`).
  - Xóa bỏ các nhãn văn bản thừa (`Sao chép`, `Giải thích lại`).
  - Đảm bảo mỗi icon có thuộc tính `title` (tooltip) tiếng Việt trực quan, phản hồi trạng thái `<Check>` xanh lá khi sao chép.
- [x] 1.2 Cập nhật thanh công cụ ở tin nhắn người dùng trong `ChatMessage.tsx`:
  - Hiển thị nút Sao chép (`<Copy>`) và nút Sửa câu hỏi (`<Pencil>` / `<Undo2>`) với tooltip *"Chỉnh sửa câu hỏi"*.
- [x] 1.3 Tinh chỉnh hiệu ứng hiển thị: Độ mờ nhẹ khi bình thường và nổi bật khi hover vào tin nhắn.

## 2. Triển Khai Cơ Chế True In-Place Regeneration
- [x] 2.1 Cập nhật `frontend/components/chat/ChatInterface.tsx`:
  - Xây dựng hàm `handleRegenerate(messageId: string)`:
    * Tìm tin nhắn người dùng liền kề trước câu trả lời của AI.
    * Xóa câu trả lời cũ khỏi state tin nhắn (`currentMessages`).
    * Kích hoạt lại luồng gọi `/chat/stream` cho đúng câu hỏi đó để tạo câu trả lời mới tại chỗ, không sinh thêm tin nhắn người dùng rác.
  - Xây dựng hàm `handleEditPrompt(promptText: string)`:
    * Đưa nội dung câu hỏi vào ô nhập liệu (`input`) và tự động focus con trỏ vào `textarea`.
- [x] 2.2 Truyền các callback `onRegenerate` và `onEditPrompt` từ `ChatInterface` vào `ChatMessage`.

## 3. Cập Nhật Kiểm Thử & Xác Minh Giao Diện
- [x] 3.1 Cập nhật kịch bản kiểm thử frontend `frontend/scripts/verify-chat-ux.mjs`:
  - Xác minh sự tồn tại của các nút icon-only và thuộc tính tooltip.
  - Xác minh cấu trúc thanh công cụ mới không chứa nhãn text gây hiểu lầm.
- [x] 3.2 Chạy toàn bộ bộ kiểm thử frontend: `npm run verify:chat-ux`.
- [x] 3.3 Đảm bảo toàn bộ test suite backend vẫn pass 100%: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/`.
- [x] 3.4 Kiểm tra trực tiếp trên trình duyệt hoạt động thực tế của tính năng Copy, Regenerate tại chỗ và Sửa câu hỏi.
