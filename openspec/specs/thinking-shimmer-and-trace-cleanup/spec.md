# thinking-shimmer-and-trace-cleanup Specification

## Purpose
Tinh giản tối đa giao diện tiến trình xử lý câu hỏi pháp lý:
1. Chuyển đổi trạng thái chờ xử lý sang dạng text thuần túy với hiệu ứng ánh sáng gradient chuyển động (Shimmering Thinking Text).
2. Xóa bỏ hoàn toàn pill button và bảng danh sách quá trình sau khi câu trả lời hoàn thành, giữ giao diện sạch sẽ, thoáng đãng.

## Requirements

### Requirement: Shimmering Thinking Text Indicator
Giao diện tin nhắn SHALL hiển thị trạng thái xử lý dạng dòng text thanh nhã với hiệu ứng shimmering gradient chuyển động trong suốt các bước xử lý câu hỏi, không sử dụng khung viền hay cấu trúc bảng.

#### Scenario: Active processing stages
- **WHEN** AI đang phân tích, tra cứu căn cứ hoặc tổng hợp câu trả lời (`analyzing`, `searching`, `selecting`, `generating`)
- **THEN** giao diện hiển thị dòng text thuần túy đi kèm icon `Sparkles` nhỏ với hiệu ứng gradient ánh sáng lướt qua (`animate-thinking-shimmer`).
- **AND THEN** không có khung viền (`border`), nền hộp (`background`) hay nút bấm thu gọn/mở rộng.

---

### Requirement: Complete Process Trace Removal on Completion
Giao diện tin nhắn SHALL ẩn/xóa hoàn toàn component tiến trình xử lý ngay khi câu trả lời hoàn thành (`completed`), không lưu lại bất kỳ nút bấm hay bảng chi tiết nào.

#### Scenario: Completion of assistant message
- **WHEN** trợ lý AI hoàn tất sinh câu trả lời (`stage === 'completed'`)
- **THEN** component tiến trình trả về `null` hoàn toàn.
- **AND THEN** không hiển thị pill button *"Tra cứu hoàn tất"* hoặc nút *"Xem quá trình"*.
- **AND THEN** không có danh sách timeline nào được lưu vết trong tin nhắn đã hoàn thiện.

---

### Requirement: Conditional Visibility of Thinking Trace on Stream
Giao diện tin nhắn SHALL chỉ hiển thị chỉ báo tiến trình suy nghĩ (`ChatProcessingTrace`) khi nội dung câu trả lời chưa bắt đầu được sinh (`!message.content?.trim()`).

#### Scenario: Streaming content arrives
- **WHEN** AI bắt đầu sinh các token đầu tiên của câu trả lời (`message.content` có độ dài > 0)
- **THEN** dòng tiến trình thinking trace lập tức unmount và biến mất khỏi giao diện, chỉ hiển thị văn bản đang stream kèm con trỏ gõ chữ.
