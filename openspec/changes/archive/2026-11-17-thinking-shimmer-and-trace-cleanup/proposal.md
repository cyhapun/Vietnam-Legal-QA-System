# Proposal: Shimmering Thinking Text & Trace Cleanup

## 1. Problem Statement
Hiện tại, giao diện chat của VietLaw AI sử dụng component `ChatProcessingTrace` để phản ánh các bước xử lý câu hỏi pháp lý. Tuy nhiên, thiết kế hiện tại còn một số điểm bất cập gây ảnh hưởng đến trải nghiệm người dùng:
1. **Dư thừa sau khi hoàn thành**: Khi câu trả lời của AI đã sinh xong (`completed`), nút pill button `✨ Tra cứu hoàn tất  Xem quá trình ⌄` vẫn tiếp tục tồn tại cố định ở chân câu trả lời. Điều này làm rối mắt, chiếm dụng diện tích thị giác và khiến tin nhắn trông nặng nề.
2. **Cấu trúc dạng bảng/hộp kỹ thuật (Boxy & Clunky)**: Component được bọc trong các viền `border`, `background` màu xám/trắng đục và danh sách timeline `ol` dài khi mở rộng, tạo cảm giác như một chiếc bảng thông số kỹ thuật nội bộ thay vì một trợ lý AI thông minh.
3. **Thiếu cảm giác "Thinking" sống động**: Trong thời gian chờ AI phân tích và tra cứu dữ liệu pháp lý (RAG retrieval), người dùng mong muốn nhìn thấy một chỉ báo trạng thái dạng chữ (text) thanh thoát kèm hiệu ứng tư duy (thinking/shimmering) hiện đại tương tự Gemini, DeepSeek R1 hay ChatGPT.

## 2. Proposed Solution
Triển khai **Phương án 1: Shimmering Thinking Text Effect & Complete Completion Cleanup**:
1. **Hiệu ứng Shimmering Thinking Text thuần túy (Text-only)**:
   - Loại bỏ hoàn toàn viền bo (`border`), nền hộp (`background`), nút đóng mở (`Xem quá trình ⌄`) và bảng danh sách timeline.
   - Hiển thị trực tiếp dưới dạng dòng text thanh nhã (ví dụ: `✦ Đang tra cứu căn cứ pháp lý...`) với hiệu ứng dải sáng gradient chuyển động lướt ngang qua chữ (`animate-shimmer` / `bg-clip-text text-transparent bg-gradient-to-r`).
   - Tự động thay đổi nội dung text theo từng giai đoạn xử lý:
     * `analyzing`: `✦ Đang phân tích câu hỏi...`
     * `searching`: `✦ Đang tra cứu căn cứ pháp lý...`
     * `selecting`: `✦ Đang chọn lọc điều luật phù hợp...`
     * `generating`: `✦ Đang tổng hợp câu trả lời...`
2. **Tự động xóa hẳn sau khi hoàn thiện (Complete Trace Removal)**:
   - Khi câu trả lời hoàn tất (`stage === 'completed'`), component trả về `null` hoàn toàn.
   - Không lưu lại bất kỳ nút bấm, nhãn trạng thái hay bảng phụ nào trong câu trả lời hoàn chỉnh.
   - Nếu trong quá trình có lỗi hoặc bị dừng (`error` / `cancelled`), hiển thị thông báo trạng thái ngắn gọn, trang nhã.
3. **Đồng bộ hóa kiểm thử UX (`verify-chat-ux.mjs`)**:
   - Cập nhật các assertion trong script kiểm thử để xác nhận trạng thái thinking text và kiểm tra việc không còn render pill/bảng thừa sau khi hoàn tất.

## 3. Goals & Non-Goals
### Goals
- Xóa bỏ 100% pill button và bảng quá trình sau khi câu trả lời hoàn thành.
- Mang lại hiệu ứng thinking text shimmering sang trọng, hiện đại, không khung viền.
- Tương thích hoàn hảo cả Light Mode và Dark Mode.
- Bảo đảm toàn bộ bộ kiểm thử UX frontend và backend pytest vượt qua 100%.

### Non-Goals
- Không thay đổi logic truy vấn RAG hay thứ tự các bước xử lý ở backend.
- Không thay đổi luồng truyền SSE event (`context`, `token`, `done`, `error`) giữa client và server.
