# Proposal: Hide Thinking Trace on Answer Streaming

## 1. Problem Statement
Trong phiên bản hiện tại, khi AI bắt đầu tuôn ra các token của câu trả lời (`stage === 'generating'`), nội dung văn bản câu trả lời đã bắt đầu gõ trực tiếp trên màn hình (`message.content` có ký tự). Tuy nhiên, dòng chữ tiến trình `✦ Đang tổng hợp câu trả lời...` vẫn tiếp tục hiển thị song song ngay phía dưới câu trả lời đang gõ cho đến tận khi stream kết thúc hoàn toàn.

Điều này gây ảnh hưởng đến trải nghiệm người dùng:
1. **Phân tâm thị giác**: Người dùng đã chuyển sự chú ý sang việc đọc nội dung câu trả lời pháp lý đang được gõ ra. Dòng chữ tiến trình ở chân câu trả lời trở nên thừa thãi và gây rối mắt.
2. **Không đúng chuẩn AI hiện đại**: Các trợ lý AI hàng đầu (ChatGPT, Claude, Gemini) chỉ hiển thị trạng thái suy nghĩ / tra cứu trong lúc chờ đợi (khi chưa có chữ nào). Ngay khi chữ đầu tiên xuất hiện, chỉ báo suy nghĩ sẽ biến mất lập tức để nhường chỗ hoàn toàn cho nội dung phản hồi.

## 2. Proposed Solution
1. **Cập nhật điều kiện hiển thị của `ChatProcessingTrace` trong `ChatMessage.tsx`**:
   - Chỉ render `ChatProcessingTrace` khi **chưa có nội dung câu trả lời** (`!message.content?.trim()`).
   - Ngay khi token đầu tiên xuất hiện (dù là 1 từ đầu tiên), điều kiện `!message.content?.trim()` lập tức trở thành `false`, khiến dòng tiến trình unmount và biến mất ngay lập tức khỏi giao diện.
2. **Đồng bộ hóa kiểm thử UX (`verify-chat-ux.mjs`)**:
   - Thêm assertion kiểm chứng điều kiện `!message.content?.trim()` trong `ChatMessage.tsx` để bảo đảm không bị regression trong tương lai.

## 3. Goals & Non-Goals
### Goals
- Ẩn dòng tiến trình thinking ngay lập tức khi câu trả lời bắt đầu sinh text (streaming).
- Bảo lưu trạng thái thinking shimmering trong lúc chờ (phân tích, tra cứu, chọn lọc).
- Đảm bảo toàn bộ kiểm thử frontend và backend tiếp tục đạt 100%.

### Non-Goals
- Không thay đổi các sự kiện SSE từ backend `/chat/stream`.
- Không can thiệp vào logic gõ chữ hay hiệu ứng `typing-cursor`.
