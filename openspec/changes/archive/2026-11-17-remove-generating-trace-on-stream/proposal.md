# Proposal: Remove Generating Trace on Stream

## 1. Problem Statement
Trong quá trình streaming câu trả lời, khi backend bắt đầu gửi các token đầu tiên (`event.type === 'token'`), frontend cập nhật `processingStage = 'generating'`.

Hiện tại, component `ChatProcessingTrace.tsx` vẫn duy trì việc ánh xạ stage `'generating'` thành dòng chữ *"Đang tổng hợp câu trả lời..."*. Kết hợp với độ trễ render giữa state `content` và `processingStage`, dòng chữ này vẫn xuất hiện ở chân câu trả lời trong lúc câu trả lời đang được stream.

Điều này vi phạm nguyên tắc trải nghiệm:
- **Người dùng chỉ cần thấy tiến trình khi chưa có chữ (đang chờ)**.
- Khi chữ đã bắt đầu tuôn ra (bước `generating`), việc hiển thị thêm dòng chữ *"Đang tổng hợp câu trả lời..."* là hoàn toàn thừa thãi, gây phân tâm và làm rối khung tin nhắn.

## 2. Proposed Solution
Triển khai cơ chế **chặn kép (Dual Guard)** để loại bỏ triệt để tiến trình ở stage `'generating'`:
1. **Trong `ChatProcessingTrace.tsx`**:
   - Khai tử hoàn toàn nhãn *"Đang tổng hợp câu trả lời..."*.
   - Đặt điều kiện: `if (stage === 'idle' || stage === 'completed' || stage === 'generating') return null;`.
   - Tiến trình chỉ phục vụ 3 khâu chờ thực sự trước khi có câu trả lời:
     * `analyzing`: `✦ Đang phân tích câu hỏi...`
     * `searching`: `✦ Đang tra cứu căn cứ pháp lý...`
     * `selecting`: `✦ Đang chọn lọc thông tin phù hợp...`
2. **Trong `ChatMessage.tsx`**:
   - Cập nhật điều kiện render an toàn:
     `!message.content?.trim() && message.processingStage && !['completed', 'generating', 'idle'].includes(message.processingStage)`.
3. **Trong `verify-chat-ux.mjs`**:
   - Cập nhật danh sách các nhãn thinking text hợp lệ (chỉ còn `analyzing`, `searching`, `selecting`).
   - Kiểm tra rằng stage `'generating'` phải trả về `null` hoặc không hiển thị text.

## 3. Goals & Non-Goals
### Goals
- Loại bỏ hoàn toàn dòng chữ *"Đang tổng hợp câu trả lời..."* trong suốt thời gian streaming.
- Đảm bảo tiến trình chỉ hiển thị ở giai đoạn chờ và biến mất 100% ngay khi bắt đầu sinh câu trả lời.
- Kiểm thử UX và backend đạt 100%.

### Non-Goals
- Không thay đổi các stage logic của backend (`analyzing`, `searching`, `selecting`, `generating`, `completed`).
