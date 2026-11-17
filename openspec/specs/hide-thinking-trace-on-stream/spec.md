# hide-thinking-trace-on-stream Specification

## Purpose
Đảm bảo tiến trình xử lý (thinking trace) chỉ xuất hiện trong giai đoạn chờ (trước khi có câu trả lời) và tự động ẩn hoàn toàn ngay khi các ký tự đầu tiên của câu trả lời bắt đầu được stream ra màn hình.

## Requirements

### Requirement: Conditional Visibility of Thinking Trace
Giao diện tin nhắn SHALL chỉ hiển thị chỉ báo tiến trình suy nghĩ (`ChatProcessingTrace`) khi nội dung câu trả lời chưa bắt đầu được sinh (`!message.content?.trim()`).

#### Scenario: Streaming content arrives
- **WHEN** AI bắt đầu sinh các token đầu tiên của câu trả lời (`message.content` có độ dài > 0)
- **THEN** dòng tiến trình thinking trace lập tức unmount và biến mất khỏi giao diện.
- **AND THEN** chỉ còn văn bản câu trả lời đang stream kèm con trỏ gõ chữ được hiển thị.

#### Scenario: Pre-response waiting phase
- **WHEN** hệ thống đang phân tích hoặc tra cứu dữ liệu pháp lý và chưa có token câu trả lời nào (`!message.content?.trim()`)
- **THEN** dòng tiến trình thinking trace hiển thị bình thường với hiệu ứng shimmering gradient.

---

### Requirement: Complete Dismissal of Trace during Answer Generation
Giao diện tin nhắn SHALL trả về `null` cho component `ChatProcessingTrace` khi stage là `'generating'` và SHALL loại bỏ hoàn toàn nhãn *"Đang tổng hợp câu trả lời..."*.

#### Scenario: Stage transitions to generating
- **WHEN** hệ thống nhận được token câu trả lời và chuyển trạng thái sang `generating`
- **THEN** component `ChatProcessingTrace` trả về `null` ngay lập tức.
- **AND THEN** không xuất hiện dòng chữ *"Đang tổng hợp câu trả lời..."* trên giao diện.
