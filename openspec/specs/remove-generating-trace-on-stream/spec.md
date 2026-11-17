# remove-generating-trace-on-stream Specification

## Purpose
Đảm bảo khi hệ thống bước vào giai đoạn sinh câu trả lời (`generating` / streaming), mọi dấu vết tiến trình đều lập tức trả về `null` và không có bất kỳ dòng chữ *"Đang tổng hợp câu trả lời..."* nào được render.

## Requirements

### Requirement: Complete Dismissal of Trace during Answer Generation
Giao diện tin nhắn SHALL trả về `null` cho component `ChatProcessingTrace` khi stage là `'generating'` và SHALL loại bỏ hoàn toàn nhãn *"Đang tổng hợp câu trả lời..."*.

#### Scenario: Stage transitions to generating
- **WHEN** hệ thống nhận được token câu trả lời và chuyển trạng thái sang `generating`
- **THEN** component `ChatProcessingTrace` trả về `null` ngay lập tức.
- **AND THEN** không xuất hiện dòng chữ *"Đang tổng hợp câu trả lời..."* trên giao diện.

#### Scenario: Pre-response stages preservation
- **WHEN** hệ thống đang ở các giai đoạn trước câu trả lời (`analyzing`, `searching`, `selecting`)
- **THEN** dòng thinking text tương ứng hiển thị với hiệu ứng shimmering gradient.
