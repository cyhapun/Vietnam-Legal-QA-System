## Why

Trải nghiệm người dùng (UI/UX) và nhận diện thương hiệu trên giao diện hỏi đáp pháp luật hiện tại đang gặp các vấn đề cần hoàn thiện:
1. **Modal xác nhận xóa hội thoại bị lệch vị trí**: Do phần tử cha bọc ngoài Sidebar trong `ChatInterface.tsx` có thuộc tính `transition-transform` / `translate-x-0`, theo chuẩn CSS W3C nó biến thành containing block cho `position: fixed`. Hệ quả là modal xác nhận xóa bị ép căn giữa trong cột sidebar hẹp (288px) bên trái màn hình thay vì toàn bộ khung nhìn trình duyệt (viewport).
2. **Khung hiển thị tiến trình (Processing Trace) cồng kềnh**: Component `ChatProcessingTrace` hiện tại chiếm quá nhiều diện tích với khối hộp màu xanh đậm lớn (`p-4 bg-blue-50/60 dark:bg-blue-500/10`) và các bullet point to thô kệch, tạo cảm giác như một widget kỹ thuật hơn là trải nghiệm AI hội thoại hiện đại như Gemini hay ChatGPT.
3. **Thanh căn cứ pháp lý và Drawer gây rối mắt**: Nút bấm `[📖 Căn cứ pháp lý 5 >]` to bản ở cuối mỗi tin nhắn cùng thanh drawer trượt từ bên phải chiếm nhiều diện tích hiển thị. Trong khi đó, người dùng đọc văn bản chủ yếu dựa vào các trích dẫn điều luật gắn liền ngay trong câu trả lời (inline `<cite>`).
4. **Nhận diện thương hiệu đơn điệu**: Hệ thống chỉ dùng icon `Scale` chung chung của Lucide React ở khắp nơi (sidebar header, avatar tin nhắn, empty state, loading spinner). Việc tích hợp logo/mascot AI pháp luật chuyên nghiệp (chú robot cầm cán cân công lý với cuộn văn bản luật) sẽ nâng tầm trải nghiệm thị giác, tạo nét đặc trưng nhận diện và thân thiện hơn cho người dùng.

Cần tái cấu trúc UI để mang lại giao diện tinh tế, hiện đại, thoáng đãng theo phong cách của các chatbot hàng đầu (Gemini, ChatGPT), đồng bộ hóa logo nhận diện và khắc phục triệt để lỗi hiển thị modal.

## What Changes

- **Cập nhật Logo và Icon nhận diện thương hiệu**:
  - Chuẩn hóa hình ảnh mascot AI pháp lý mới làm `frontend/public/logo.png` và favicon `frontend/app/icon.png`.
  - Thay thế icon Lucide `Scale` bằng Logo mới tại: Header Sidebar, Avatar tin nhắn trợ lý ảo trong `frontend/components/chat/ChatMessage.tsx`, màn hình chào mừng trong `frontend/components/chat/ChatEmptyState.tsx`, và animation `frontend/components/ui/LoadingSpinner.tsx`.
- **Sửa lỗi định vị Modal xác nhận xóa cuộc hội thoại**:
  - Triển khai React Portal (`createPortal(..., document.body)`) cho modal xác nhận xóa trong `frontend/components/chat/Sidebar.tsx` (hoặc đưa lên cấp `ChatInterface.tsx`), đảm bảo modal thoát khỏi containing block bị `transform` của sidebar và luôn căn chính giữa 100% màn hình trình duyệt.
  - Tối ưu hiệu ứng backdrop mờ (`backdrop-blur-sm`), z-index (`z-[100]`), và hiệu ứng xuất hiện mượt mà.
- **Tái thiết kế hiển thị tiến trình xử lý (Thinking Trace) theo chuẩn Gemini/ChatGPT**:
  - Khi đang xử lý (Analyzing, Searching, Selecting, Generating): Hiển thị trạng thái suy nghĩ tinh gọn (inline status) với icon lấp lánh (Sparkle/Brain) hoặc spinner mỏng và dòng chữ động (`Đang phân tích câu hỏi...` ➔ `Đang tra cứu pháp luật...` ➔ `Đang tổng hợp câu trả lời...`).
  - Khi hoàn tất (Completed): Tự động thu gọn thành một pill/accordion mỏng kín đáo (`✨ Đã tra cứu căn cứ pháp lý` kèm icon Chevron nhỏ), không dùng viền khung đậm.
  - Khi người dùng bấm mở rộng: Hiển thị timeline tối giản (text-xs, đường nối mỏng, tinh tế, không bullet point thô).
  - Khi gặp lỗi hoặc hủy: Hiển thị thông báo nhỏ gọn tinh tế kèm nút thử lại.
- **Loại bỏ nút Accordion và Side Drawer Căn cứ pháp lý**:
  - Gỡ bỏ component trigger `LegalSourcesTrigger` (`📖 Căn cứ pháp lý 5 >`) ở cuối mỗi tin nhắn Assistant trong `frontend/components/chat/ChatMessage.tsx`.
  - Gỡ bỏ Side Drawer trượt bên phải (`drawerContext`, `setDrawerContext`, container `#legal-sources-panel` và `LegalSourceList`) trong `frontend/components/chat/ChatInterface.tsx`.
  - **Bảo lưu đầy đủ**: Giữ nguyên vẹn cơ chế trích dẫn inline `<cite id="...">` trong văn bản Markdown câu trả lời và `CitationModal` pop-up khi người dùng click vào tên điều luật.
- **Đồng bộ hóa Script kiểm thử UX**:
  - Cập nhật file `frontend/scripts/verify-chat-ux.mjs` để tương thích hoàn toàn với kiến trúc UX mới (bỏ các assertion về `LegalSourcesTrigger` và `legal-sources-panel`, kiểm tra thinking trace mới, logo và modal xóa).

## Capabilities

### Modified Capabilities

- `chat-ui-ux-enhancements`: Cải tiến giao diện chat, chuyển đổi khung tiến trình sang phong cách Gemini/ChatGPT, cập nhật nhận diện logo/icon thương hiệu, sửa triệt để định vị modal xác nhận xóa và tinh gọn phần trích dẫn căn cứ.

## Impact

- **Frontend**:
  - Trải nghiệm thị giác hiện đại, sạch sẽ và chuyên nghiệp; nhận diện thương hiệu rõ nét, thân thiện.
  - Modal xác nhận xóa hiển thị chuẩn mực ở chính giữa toàn màn hình trên mọi kích thước thiết bị.
  - Loại bỏ các thành phần DOM và state thừa (`drawerContext`, `isSourcesPanelOpen`, `LegalSourcesTrigger`).
- **Backend**: Không yêu cầu thay đổi backend.
