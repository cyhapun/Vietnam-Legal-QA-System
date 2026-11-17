# server-authoritative-config Specification

## Purpose
Đảm bảo toàn bộ các tham số thực thi của pipeline RAG (retrieval, reranking, caching, context budget) và việc cấp phép API Key của mô hình LLM được cố định an toàn và quản lý tập trung ở phía máy chủ, đồng thời xóa bỏ toàn bộ bề mặt quản trị và cấu hình không cần thiết trên giao diện người dùng.

## Requirements

### Requirement: Removal of administrative UI and endpoints
Hệ thống SHALL gỡ bỏ hoàn toàn giao diện trang `/admin`, các thành phần cấu hình hệ thống trên frontend và router quản trị `/api/admin` trên backend.

#### Scenario: User navigates to /admin
- **WHEN** người dùng điều hướng tới đường dẫn `/admin` trên trình duyệt
- **THEN** máy chủ trả về trạng thái 404 Not Found hoặc chuyển hướng về trang chủ.

#### Scenario: Client requests /api/admin
- **WHEN** client gửi yêu cầu tới bất kỳ endpoint nào thuộc `/api/admin`
- **THEN** backend phản hồi mã trạng thái 404 Not Found.

#### Scenario: Sidebar navigation items
- **WHEN** người dùng mở giao diện chat
- **THEN** thanh điều hướng bên trái chỉ hiển thị tùy chọn "Đoạn chat mới", không hiển thị mục "Quản trị" hay "Kho Tài Liệu".

### Requirement: Server-authoritative pipeline controls
Hệ thống SHALL thực thi toàn bộ logic của pipeline RAG (retrieval candidate limit, Cross-Encoder reranker, Semantic Cache, Context token budget) theo cấu hình của máy chủ và SHALL NOT cho phép client ghi đè các tham số này thông qua chat request.

#### Scenario: Client sends chat request without pipeline flags
- **WHEN** frontend gửi `POST /api/chat` chỉ chứa nội dung tin nhắn, session ID và danh mục luật
- **THEN** backend tự động áp dụng cấu hình chuẩn từ `app/config.py` và biến môi trường server để thực thi đầy đủ các bước tìm kiếm hybrid, reranking và kiểm tra cache.

#### Scenario: Inability of client to disable reranker
- **WHEN** backend xử lý một truy vấn tra cứu pháp luật
- **THEN** Cross-Encoder Reranker luôn được kích hoạt theo cấu hình server nhằm bảo đảm chất lượng trích dẫn, bất kể nội dung payload từ client.

### Requirement: Fixed Google AI Studio inference
Hệ thống SHALL cố định nhà cung cấp mô hình ngôn ngữ lớn (LLM) là Google AI Studio với mô hình `gemini-3.1-flash-lite` và sử dụng biến môi trường máy chủ `GOOGLE_API_KEY`.

#### Scenario: Answer generation with server credentials
- **WHEN** câu hỏi pháp lý được gửi đến để sinh câu trả lời
- **THEN** backend sử dụng `GOOGLE_API_KEY` từ file `.env` trên máy chủ để kết nối tới Google AI Studio.

#### Scenario: Absence of client-side credentials
- **WHEN** người dùng lần đầu truy cập hệ thống
- **THEN** không xuất hiện bất kỳ popup nào yêu cầu nhập API Key cá nhân và không yêu cầu lưu trữ khóa trong trình duyệt.
