# chat-actions-refinement-and-regenerate Specification

## Purpose
Tinh giản và hiện đại hóa thanh công cụ thao tác tin nhắn (Message Action Toolbar) của VietLaw AI theo tiêu chuẩn thiết kế quốc tế (ChatGPT, Claude):
1. Chuyển đổi toàn bộ nút sang dạng Icon-Only tối giản, hỗ trợ Tooltip tiếng Việt rõ ràng và hiệu ứng phản hồi trực quan.
2. Hiện thực hóa cơ chế True Regenerate: Bấm nút tạo lại sẽ sinh lại câu trả lời mới tại chỗ cho đúng câu hỏi của lượt đó, không làm phình to lịch sử trò chuyện.
3. Bổ sung nút sửa nhanh câu hỏi trên tin nhắn người dùng.

## Requirements

### Requirement: Minimalist Icon-Only Action Toolbar
Giao diện tin nhắn SHALL hiển thị thanh công cụ tối giản chỉ gồm các icon nhỏ gọn (icon-only) kèm tooltip tiếng Việt, thay thế các nút dạng text cồng kềnh trước đây.

#### Scenario: Assistant message toolbar rendering
- **WHEN** một câu trả lời của AI được hiển thị hoàn chỉnh
- **THEN** thanh công cụ dưới chân câu trả lời hiển thị các nút icon riêng biệt: Sao chép (`<Copy>`), Tạo lại câu trả lời (`<RotateCcw>`), Hữu ích (`<ThumbsUp>`), và Báo cáo (`<ThumbsDown>`).
- **AND THEN** mỗi icon có thuộc tính `title` hoặc tooltip hiển thị chức năng rõ ràng khi rê chuột.
- **AND THEN** không có các đoạn text thừa thãi chiếm dụng diện tích hiển thị.

#### Scenario: Visual feedback on copy
- **WHEN** người dùng click vào nút icon Sao chép
- **THEN** nội dung tin nhắn được sao chép vào Clipboard của hệ điều hành.
- **AND THEN** icon chuyển sang dấu tích xanh (`<Check className="text-emerald-500">`) và tooltip cập nhật thành *"Đã chép!"* trong 2 giây.

---

### Requirement: True In-Place Answer Regeneration
Hệ thống SHALL cho phép người dùng sinh lại (regenerate) câu trả lời của AI tại chỗ bằng cách gọi lại mô hình với câu hỏi gốc của lượt đó mà không tạo thêm tin nhắn người dùng mới vào lịch sử hội thoại.

#### Scenario: Regenerating an assistant answer
- **WHEN** người dùng click vào nút icon Tạo lại (`<RotateCcw>`) dưới câu trả lời của AI
- **THEN** câu trả lời cũ của AI được xóa khỏi giao diện và thay thế bằng luồng stream câu trả lời mới (`/chat/stream`).
- **AND THEN** không có tin nhắn người dùng mới *"Giải thích đơn giản hơn..."* nào bị chèn thêm vào danh sách tin nhắn.
- **AND THEN** toàn bộ bối cảnh căn cứ pháp lý và câu trả lời mới được cập nhật hoàn chỉnh sau khi stream hoàn tất.

---

### Requirement: Quick User Prompt Editing
Giao diện tin nhắn người dùng SHALL cung cấp nút thao tác nhanh để nạp lại nội dung câu hỏi vào khung nhập liệu giúp người dùng dễ dàng chỉnh sửa câu hỏi.

#### Scenario: Editing user prompt
- **WHEN** người dùng click vào nút Chỉnh sửa câu hỏi (`<Pencil>` hoặc `<Undo2>`) ở chân tin nhắn người dùng
- **THEN** nội dung câu hỏi đó được đưa vào ô nhập liệu (`textarea`) và tự động focus con trỏ.
