# rag-pipeline-refactoring Specification

## Purpose
Tái cấu trúc, chuẩn hóa kiến trúc và tối ưu hóa hiệu năng cho RAG Pipeline backend của hệ thống tư vấn pháp luật: loại bỏ mã nguồn chết, khử trùng lặp logic điều phối giữa stream và non-stream, khắc phục các lỗi mã hóa ký tự tiếng Việt, loại bỏ cảnh báo deprecation khi khởi động và tối ưu hóa các điểm nghẽn thuật toán trong sinh vector thưa và pipeline reflection.

## Requirements

### Requirement: Dead code elimination and legacy module cleanup
Hệ thống SHALL loại bỏ hoàn toàn các file mồ côi và biến toàn cục không còn được sử dụng để duy trì cấu trúc module minh bạch.

#### Scenario: Deleting unused rag service module
- **WHEN** kiểm tra toàn bộ cây mã nguồn backend
- **THEN** file `backend/app/services/rag.py` không còn tồn tại trong kho mã nguồn.
- **AND THEN** toàn bộ hệ thống và các test suites tiếp tục hoạt động bình thường mà không phát sinh `ImportError`.

#### Scenario: Cleaning redundant structures in legacy vectorstore
- **WHEN** module `backend/app/api/documents.py` hoặc các service khác cần xử lý embedding/ingestion
- **THEN** việc gọi ingestion sử dụng trực tiếp các thành phần chuẩn hóa từ `pipeline.py` và `knowledge_base.py`.

### Requirement: Unified RAG turn orchestration in chat endpoints
Hệ thống SHALL đóng gói logic điều phối RAG dùng chung (bao gồm xây dựng bối cảnh hội thoại, query rewriting, kiểm tra semantic cache, truy xuất tài liệu, xác thực trích dẫn, cập nhật cache và lưu trữ turn) thành các hàm/module tập trung, tránh trùng lặp giữa hai endpoint `POST /chat` và `POST /chat/stream`.

#### Scenario: Handling non-streaming chat request
- **WHEN** client gửi yêu cầu đến `POST /chat`
- **THEN** endpoint sử dụng hàm điều phối tập trung để chuẩn bị ngữ cảnh và xử lý hậu kỳ (citation validation, cache update, persistence).
- **AND THEN** phản hồi trả về đúng schema JSON `{"text": ..., "contextUsed": ...}`.

#### Scenario: Handling streaming chat request
- **WHEN** client gửi yêu cầu đến `POST /chat/stream`
- **THEN** endpoint sử dụng chung logic chuẩn bị ngữ cảnh và hậu kỳ với endpoint non-stream.
- **AND THEN** các sự kiện SSE (`context`, `token`, `done`, `error`) được truyền phát liên tục và chính xác đến client.

#### Scenario: Semantic cache hit on streaming and non-streaming
- **WHEN** câu hỏi của người dùng có độ tương đồng vượt ngưỡng `SEMANTIC_CACHE_THRESHOLD`
- **THEN** cơ chế điều phối tập trung phát hiện cache hit và trả ngay kết quả lưu sẵn cho cả hai chế độ stream và non-stream mà không kích hoạt gọi lại LLM.

### Requirement: Encoding and syntax error remediation
Hệ thống SHALL đảm bảo toàn bộ chuỗi thông báo lỗi và luồng xử lý điều kiện được chuẩn hóa chính xác, không bị lỗi mã hóa UTF-8 hoặc lặp điều kiện logic.

#### Scenario: LLM provider unavailable error message
- **WHEN** không có bất kỳ LLM provider nào khả dụng
- **THEN** ngoại lệ `RuntimeError` ném ra chuỗi tiếng Việt chuẩn có dấu: `"Không có LLM provider nào khả dụng. Hãy kiểm tra cấu hình provider và API key."` mà không bị lỗi Mojibake UTF-8.

#### Scenario: Deleting session endpoint validation
- **WHEN** client gọi `DELETE /chat/session/{session_id}`
- **THEN** việc kiểm tra tính hợp lệ của `session_id` chỉ thực hiện một lần duy nhất, loại bỏ khối `if` lặp lại dư thừa.

### Requirement: Runtime performance optimization
Hệ thống SHALL tối ưu hóa các điểm nghẽn tính toán trong quá trình sinh vector thưa và truy xuất pipeline.

#### Scenario: Sparse vector generation with hash collision
- **WHEN** `SparseVectorGenerator.generate_sparse_vector(text)` xử lý các văn bản có nhiều từ khóa băm trùng index
- **THEN** việc tích lũy tần suất từ khóa diễn ra trong thời gian $O(1)$ thông qua cấu trúc từ điển (hash map), không sử dụng tìm kiếm tuyến tính $O(N)$ trên danh sách mảng.

#### Scenario: Eliminating per-request signature reflection
- **WHEN** hàm `retrieve` hoặc `aretrieve` trong `RAGPipeline` được gọi
- **THEN** hệ thống không thực thi `inspect.signature` trên mỗi turn chat để kiểm tra tham số `api_key`, mà sử dụng cờ boolean đã được phân giải hoặc chuẩn hóa signature lúc khởi tạo.

### Requirement: Modern FastAPI lifespan startup migration
Hệ thống SHALL sử dụng async context manager `lifespan` thay thế cho `@application.on_event("startup")` để tương thích hoàn toàn với các phiên bản FastAPI hiện đại.

#### Scenario: Application startup and health checks
- **WHEN** server FastAPI khởi động
- **THEN** các tác vụ nạp metadata kiến thức, kiểm tra cấu hình lưu trữ và preload model chạy suôn sẻ mà không kích hoạt cảnh báo `DeprecationWarning: on_event is deprecated`.
- **AND THEN** các endpoint `/health` và `/readiness` phản hồi chính xác trạng thái sẵn sàng của dịch vụ.
