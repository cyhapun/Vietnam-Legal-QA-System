# Tasks: Refactor RAG Pipeline & Codebase Cleanup

## 1. Dọn Dẹp Mã Nguồn Thừa (Dead Code Removal)
- [x] 1.1 Xóa bỏ file mồ côi `backend/app/services/rag.py`.
- [x] 1.2 Dọn dẹp các biến toàn cục không cần thiết trong `backend/app/services/vectorstore.py` và chuẩn hóa import trong `backend/app/api/documents.py`.
- [x] 1.3 Kiểm tra toàn bộ codebase để đảm bảo không còn bất kỳ import dangling nào trỏ đến `rag.py`.

## 2. Khắc Phục Lỗi Mã Hóa & Chuẩn Hóa Khởi Động
- [x] 2.1 Sửa lỗi Mojibake tiếng Việt trong `backend/app/services/llm.py` (dòng 338) thành chuỗi có dấu chuẩn xác.
- [x] 2.2 Loại bỏ khối kiểm tra `session_id` bị lặp lại dư thừa trong hàm `delete_session` của `backend/app/api/chat.py`.
- [x] 2.3 Chuyển đổi `@application.on_event("startup")` trong `backend/app/main.py` sang async context manager `lifespan(app: FastAPI)` hiện đại.

## 3. Tối Ưu Hóa Hiệu Năng Thực Thi (Micro-optimizations)
- [x] 3.1 Cải tiến `SparseVectorGenerator` trong `backend/app/services/sparse_vector.py`: dùng dictionary `{index: value}` để xử lý collision trong $O(1)$ thay vì tìm kiếm tuyến tính $O(N)$ trên list.
- [x] 3.2 Tối ưu hóa `RAGPipeline` trong `backend/app/services/pipeline.py`: loại bỏ `inspect.signature` ở hot-path của `retrieve` và `aretrieve`, phân giải khả năng nhận `api_key` một lần duy nhất lúc khởi tạo.

## 4. Tái Cấu Trúc Bộ Điều Phối RAG (api/chat.py)
- [x] 4.1 Tạo module điều phối `backend/app/services/chat_orchestrator.py` đóng gói các bước dùng chung (`prepare_turn_context`, `retrieve_turn_context`, `finalize_turn`).
- [x] 4.2 Tái cấu trúc `chat_endpoint` (non-streaming) sử dụng các helper từ `chat_orchestrator.py`.
- [x] 4.3 Tái cấu trúc `chat_stream_endpoint` (streaming) sử dụng các helper từ `chat_orchestrator.py`.
- [x] 4.4 Đảm bảo tính nhất quán giữa hai luồng: xử lý Semantic Cache hit, chuẩn hóa bối cảnh, xác thực trích dẫn `<cite id="...">`, cập nhật cache và lưu turn vào PostgreSQL.

## 5. Kiểm Thử & Xác Minh Toàn Diện
- [x] 5.1 Chạy toàn bộ test suite backend `PYTHONPATH=. .venv/bin/pytest tests/` đảm bảo 124/124 tests pass.
- [x] 5.2 Khởi động lại backend server, kiểm tra log startup sạch sẽ, không có `DeprecationWarning` và các endpoint `/health`, `/readiness` đạt 200 OK.
- [x] 5.3 Gửi request kiểm thử thực tế đến cả `POST /chat` và `POST /chat/stream` để xác nhận RAG pipeline hoạt động trơn tru.
