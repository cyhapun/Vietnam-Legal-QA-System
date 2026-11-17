# Proposal: Chat Actions Refinement & True Answer Regeneration

## Why

Thanh công cụ thao tác nhanh dưới chân tin nhắn (Action Toolbar) hiện tại của VietLaw AI đang tồn tại các hạn chế về mặt giao diện và trải nghiệm người dùng (UI/UX) khi đối chiếu với các tiêu chuẩn thiết kế của các chatbot AI hàng đầu (ChatGPT, Claude):

1. **Hiển thị rườm rà (Text + Icon):** Các nút thao tác ở chân câu trả lời đang hiển thị đồng thời cả icon và chữ (`[icon] Sao chép`, `[icon] Giải thích lại`). Cách hiển thị này chiếm nhiều diện tích ngang, gây vỡ dòng trên màn hình hẹp (mobile) và làm giảm tính thanh thoát của giao diện.
2. **Cơ chế gây hiểu lầm của nút "Giải thích lại":** Nút sử dụng icon xoay tròn `<RotateCcw>` (biểu tượng phổ quát cho tính năng *Tạo lại / Regenerate* trong các hệ thống AI), nhưng khi click lại tự động gửi thêm một tin nhắn người dùng mới với nội dung *"Giải thích đơn giản hơn với ví dụ thực tế"*. Điều này khiến phiên chat bị phình to lịch sử và không đúng với kỳ vọng của người dùng khi họ chỉ muốn AI sinh lại câu trả lời khác cho câu hỏi đó.
3. **Thiếu cơ chế "Regenerate" thực thụ (In-Place Regeneration):** Người dùng chưa có cách nào để yêu cầu hệ thống sinh lại câu trả lời thay thế câu trả lời chưa ưng ý tại đúng lượt chat đó mà không bị ô nhiễm lịch sử hội thoại.
4. **Trải nghiệm thao tác trên tin nhắn người dùng chưa tối ưu:** Cần hoàn thiện nút sửa/tái sử dụng câu hỏi (Edit Prompt) ở tin nhắn người dùng để nhanh chóng đưa lại nội dung vào ô nhập liệu khi muốn chỉnh sửa câu hỏi.

## What Changes

- **Chuyển đổi sang Cụm Công cụ Icon-Only Thanh Lịch (ChatGPT / Claude Standard):**
  - Chuyển toàn bộ các nút ở footer câu trả lời AI sang dạng **icon-only với tooltip tiếng Việt trực quan**:
    - `<Copy>`: *"Sao chép câu trả lời"* $\rightarrow$ khi click chuyển sang `<Check>` màu xanh ngọc bích *"Đã chép!"*.
    - `<RotateCcw>`: *"Tạo lại câu trả lời"* (Regenerate).
    - `<ThumbsUp>`: *"Câu trả lời hữu ích"*.
    - `<ThumbsDown>`: *"Báo cáo câu trả lời chưa chuẩn"* (kèm Negative Feedback Popover).
  - Hiển thị tinh tế: Cụm nút có độ mờ nhẹ (`opacity-70`) và sáng rõ (`opacity-100`) khi người dùng di chuột vào tin nhắn.
- **Hiện thực hóa Cơ chế True Regenerate (Tạo lại câu trả lời tại chỗ):**
  - Khi click `<RotateCcw>` trên câu trả lời của AI:
    - Tìm câu hỏi của người dùng tương ứng với lượt đó.
    - Xóa câu trả lời hiện tại của AI khỏi danh sách tin nhắn hiển thị (và local state).
    - Tự động kích hoạt lại luồng sinh `/chat/stream` cho đúng câu hỏi đó để tạo câu trả lời mới tại chỗ, không sinh thêm tin nhắn người dùng rác.
- **Tinh chỉnh Thao tác ở Tin nhắn Người Dùng (User Message Actions):**
  - Bổ sung nút "Sửa câu hỏi" (icon `<Pencil>` hoặc `<Undo2>`) với tooltip *"Chỉnh sửa câu hỏi"*. Khi click, đưa toàn bộ nội dung tin nhắn lên ô nhập liệu (`textarea`) và tự động focus.
- **Bảo toàn và Tinh chỉnh Popover Phản hồi (Feedback Popover):**
  - Duy trì liên kết với API `/api/feedback` và bảng `chat_feedbacks` trong PostgreSQL khi bấm Thumbs Up / Thumbs Down.

## Capabilities

### New Capabilities
- `true-answer-regeneration`: Cơ chế tạo lại câu trả lời tại chỗ cho lượt chat của AI, thay thế nội dung cũ bằng câu trả lời mới mà không làm tăng số lượt tin nhắn hội thoại.

### Modified Capabilities
- `chat-message-actions-toolbar`: Tinh giản thanh công cụ tin nhắn sang dạng icon-only tối giản, hỗ trợ tooltip mượt mà và hiệu ứng phản hồi trực quan.

## Impact
- **Thẩm mỹ giao diện:** Giao diện tin nhắn trở nên chuyên nghiệp, thanh thoát, đồng bộ hoàn hảo với xu hướng thiết kế của ChatGPT, Claude.
- **Hiệu quả tương tác:** Người dùng có thể dễ dàng sinh lại câu trả lời hoặc sửa nhanh câu hỏi chỉ với một cú click chuột.
- **Tính toàn vẹn dữ liệu:** Lịch sử hội thoại trong PostgreSQL không bị chèn các tin nhắn mẫu cố định thừa thãi.
