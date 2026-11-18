# refined-chat-ui Specification

## Purpose
Nâng cao trải nghiệm người dùng và nhận diện thương hiệu trên giao diện hỏi đáp pháp luật thông qua việc đồng bộ hóa logo mascot AI pháp luật, hiển thị tiến trình xử lý tinh gọn theo phong cách Gemini/ChatGPT, đảm bảo modal xác nhận xóa cuộc hội thoại luôn được căn chính giữa toàn bộ màn hình, tối ưu bố cục mở rộng toàn màn hình (full-width) khi toggle Sidebar, và loại bỏ các thành phần trigger/drawer căn cứ pháp lý dư thừa trong khi vẫn bảo tồn khả năng tra cứu trích dẫn inline trực tiếp trong câu trả lời.

## Requirements

### Requirement: Brand logo and mascot presentation
Hệ thống SHALL sử dụng thống nhất logo/mascot AI pháp luật chuyên nghiệp thay thế cho icon `Scale` chung chung tại các vị trí nhận diện thương hiệu chính.

#### Scenario: Displaying sidebar header logo
- **WHEN** người dùng quan sát thanh Sidebar bên trái
- **THEN** tiêu đề VietLaw AI hiển thị cùng logo mascot bo góc tinh tế với hiệu ứng đổ bóng.

#### Scenario: Displaying assistant chat avatar
- **WHEN** trợ lý AI gửi câu trả lời trong cuộc hội thoại
- **THEN** avatar tin nhắn của trợ lý hiển thị hình ảnh mascot robot đại diện cho VietLaw AI.

#### Scenario: Displaying welcome screen logo
- **WHEN** người dùng mở một phiên chat mới (empty state)
- **THEN** màn hình chào mừng hiển thị hình ảnh mascot logo nổi bật ở vị trí trung tâm.

#### Scenario: Favicon and App icon
- **WHEN** người dùng mở ứng dụng trên trình duyệt web
- **THEN** tab trình duyệt hiển thị favicon tương ứng với logo mascot mới.

### Requirement: Viewport-centered delete confirmation modal
Hệ thống SHALL hiển thị modal xác nhận xóa cuộc hội thoại chính giữa toàn bộ khung nhìn trình duyệt (viewport) mà không bị giới hạn hay lệch bởi thuộc tính biến đổi CSS (`transform`) của Sidebar.

#### Scenario: User clicks delete session button in sidebar
- **WHEN** người dùng nhấn vào biểu tượng thùng rác của một phiên chat trên Sidebar
- **THEN** modal xác nhận xóa xuất hiện ở chính giữa 100% màn hình trình duyệt (viewport center) với lớp phủ mờ (backdrop blur) che toàn bộ màn hình.

#### Scenario: User cancels deletion
- **WHEN** người dùng nhấn "Hủy bỏ" hoặc nhấp chuột vào vùng backdrop bên ngoài modal
- **THEN** modal đóng lại và phiên chat vẫn được giữ nguyên.

#### Scenario: User confirms deletion
- **WHEN** người dùng nhấn "Xác nhận xóa"
- **THEN** phiên chat được xóa khỏi cơ sở dữ liệu và modal được đóng lại.

### Requirement: Shimmering thinking text and complete trace removal
Hệ thống SHALL hiển thị tiến trình xử lý dưới dạng dòng text thinking thuần túy với hiệu ứng gradient chuyển động (shimmering wave) trong lúc chờ câu trả lời, và SHALL tự động xóa bỏ hoàn toàn tiến trình sau khi hoàn tất đoạn chat.

#### Scenario: AI is processing the question
- **WHEN** hệ thống đang thực hiện các bước xử lý câu hỏi (`analyzing`, `searching`, `selecting`, hoặc `generating`)
- **THEN** giao diện hiển thị dòng text thuần túy thanh thoát kèm icon `Sparkles` nhỏ với hiệu ứng gradient ánh sáng lướt qua (`animate-thinking-shimmer`), không hiển thị khung viền hay cấu trúc bảng.

#### Scenario: AI completes the response
- **WHEN** quá trình sinh câu trả lời hoàn tất (`completed`)
- **THEN** component tiến trình trả về `null` và biến mất hoàn toàn khỏi DOM, không hiển thị pill button hay bảng danh sách quá trình nào.

### Requirement: Responsive full-width chat layout on sidebar toggle
Hệ thống SHALL thu gọn hoàn toàn chiều rộng của Sidebar về 0 (`w-0`) khi người dùng đóng Sidebar trên desktop (`≥ 1024px`, `lg:`), đảm bảo khung chat chính mở rộng phủ kín 100% chiều ngang màn hình mà không để lại khoảng trống thừa; đồng thời trên mobile và tablet (`< 1024px`) Sidebar hoạt động dạng overlay drawer mặc định đóng.

#### Scenario: User collapses sidebar on desktop
- **WHEN** người dùng bấm nút đóng Sidebar trên giao diện desktop (`≥ 1024px`)
- **THEN** Sidebar chuyển trạng thái sang `w-0` và ẩn hoàn toàn, đồng thời khung chat `flex-1` mở rộng chiếm trọn 100% viewport.
- **AND THEN** nút mở Sidebar (`PanelLeft`) xuất hiện ở góc trên bên trái của header.

#### Scenario: User reopens sidebar
- **WHEN** người dùng nhấn nút mở Sidebar ở góc trên bên trái
- **THEN** Sidebar mở rộng trở lại kích thước tiêu chuẩn (`lg:w-64` trên desktop hoặc overlay drawer `w-[82vw] max-w-[300px]` trên `< 1024px`) với hiệu ứng chuyển cảnh mượt mà.

### Requirement: Inline citation links preservation and removal of redundant bottom trigger & side drawer
Hệ thống SHALL loại bỏ nút trigger `[📖 Căn cứ pháp lý 5 >]` ở chân mỗi tin nhắn và thanh Side Drawer trượt bên phải, đồng thời SHALL bảo lưu toàn bộ các liên kết trích dẫn `<cite>` trực tiếp trong văn bản câu trả lời kèm modal tra cứu chi tiết điều luật được render qua `createPortal` tới `document.body`.

#### Scenario: Viewing assistant message
- **WHEN** câu trả lời của trợ lý AI được hiển thị
- **THEN** không xuất hiện nút bấm trigger `[📖 Căn cứ pháp lý ...]` và không có ngăn kéo Side Drawer bên phải màn hình.

#### Scenario: Clicking an inline citation link
- **WHEN** người dùng nhấp vào tên một điều luật được trích dẫn trong văn bản câu trả lời (ví dụ: `Luật Đất đai 2024, Điều 27, Khoản 3`)
- **THEN** modal chi tiết điều luật (`CitationModal`) được render qua `createPortal` tới `document.body`, hiển thị dạng bottom sheet trên mobile (`< sm`) và modal căn giữa trên tablet/desktop (`sm+`).

### Requirement: UX test suite alignment
Hệ thống SHALL đồng bộ hóa script kiểm thử UX `frontend/scripts/verify-chat-ux.mjs` để kiểm chứng đúng thiết kế giao diện mới và đảm bảo tất cả bài kiểm thử đều vượt qua.

#### Scenario: Executing verify-chat-ux script
- **WHEN** kiểm thử viên hoặc CI chạy `npm run verify:chat-ux`
- **THEN** script kiểm thử hoàn tất thành công mà không có lỗi thiếu component hoặc vi phạm cấu trúc UX.
