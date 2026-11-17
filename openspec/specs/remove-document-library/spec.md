# remove-document-library Specification

## Purpose
Đảm bảo giao diện người dùng chỉ tập trung vào chức năng trợ lý hỏi đáp pháp luật thông minh, loại bỏ hoàn toàn nút bấm, trang hiển thị và các component thuộc module "Kho Tài Liệu" trên frontend, đồng thời chuyển hướng mọi truy cập `/docs` về trang chủ.

## Requirements

### Requirement: Removal of Document Library Navigation from Sidebar
Thanh điều hướng bên trái (`Sidebar.tsx`) SHALL loại bỏ nút "Kho Tài Liệu" và icon `LibraryBig`, chỉ hiển thị tùy chọn hành động "Đoạn chat mới" (`+ Đoạn chat mới`).

#### Scenario: User opens the sidebar
- **WHEN** người dùng mở thanh sidebar trên giao diện máy tính hoặc thiết bị di động
- **THEN** thanh sidebar hiển thị nút "+ Đoạn chat mới" và thanh tìm kiếm
- **AND THEN** không xuất hiện nút "Kho Tài Liệu" hoặc liên kết dẫn tới `/docs`.

### Requirement: Removal of Document Library Pages, Components, and Proxy Routes
Hệ thống frontend SHALL gỡ bỏ hoàn toàn trang dashboard `/docs`, thư mục component `components/docs/`, và route API proxy `/api/documents/`.

#### Scenario: Codebase integrity check
- **WHEN** kiểm tra cấu trúc mã nguồn frontend
- **THEN** thư mục `frontend/app/docs/` không tồn tại
- **AND THEN** thư mục `frontend/components/docs/` không tồn tại
- **AND THEN** thư mục `frontend/app/api/documents/` không tồn tại.

### Requirement: Automatic Redirection of /docs to Home
Next.js server SHALL tự động chuyển hướng mọi yêu cầu HTTP điều hướng tới `/docs` về trang chủ `/`.

#### Scenario: User visits /docs URL directly
- **WHEN** người dùng truy cập trực tiếp URL `/docs` trên trình duyệt
- **THEN** máy chủ phản hồi trạng thái chuyển hướng (307 Redirect) đưa người dùng về `/`.
