# Delta Spec: refined-chat-ui

## MODIFIED Requirements

### Requirement: Responsive full-width chat layout on sidebar toggle
Hệ thống SHALL thu gọn hoàn toàn chiều rộng của Sidebar về 0 (`w-0`) khi người dùng đóng Sidebar trên desktop (`≥ 1024px`, `lg:`), đảm bảo khung chat chính mở rộng phủ kín 100% chiều ngang màn hình mà không để lại khoảng trống thừa; đồng thời trên mobile và tablet (`< 1024px`) Sidebar hoạt động dạng overlay drawer mặc định đóng.

#### Scenario: User collapses sidebar on desktop
- **WHEN** người dùng bấm nút đóng Sidebar trên giao diện desktop (`≥ 1024px`)
- **THEN** Sidebar chuyển trạng thái sang `w-0` và ẩn hoàn toàn, đồng thời khung chat `flex-1` mở rộng chiếm trọn 100% viewport.
- **AND THEN** nút mở Sidebar (`PanelLeft`) xuất hiện ở góc trên bên trái của header.

#### Scenario: User reopens sidebar
- **WHEN** người dùng nhấn nút mở Sidebar ở góc trên bên trái
- **THEN** Sidebar mở rộng trở lại kích thước tiêu chuẩn (`lg:w-64` trên desktop hoặc overlay drawer `w-72 max-w-[85vw]` trên `< 1024px`) với hiệu ứng chuyển cảnh mượt mà.

### Requirement: Inline citation links preservation and removal of redundant bottom trigger & side drawer
Hệ thống SHALL loại bỏ nút trigger `[📖 Căn cứ pháp lý 5 >]` ở chân mỗi tin nhắn và thanh Side Drawer trượt bên phải, đồng thời SHALL bảo lưu toàn bộ các liên kết trích dẫn `<cite>` trực tiếp trong văn bản câu trả lời kèm modal tra cứu chi tiết điều luật được render qua `createPortal` tới `document.body`.

#### Scenario: Clicking an inline citation link
- **WHEN** người dùng nhấp vào tên một điều luật được trích dẫn trong văn bản câu trả lời (ví dụ: `Luật Đất đai 2024, Điều 27, Khoản 3`)
- **THEN** modal chi tiết điều luật (`CitationModal`) được render qua `createPortal` tới `document.body`, hiển thị dạng bottom sheet trên mobile (`< sm`) và modal căn giữa trên tablet/desktop (`sm+`).
