## Why

Pipeline RAG hiện tại đã có đầy đủ các thành phần cốt lõi (Hybrid Search BM25 + Dense Qdrant, Cross-Encoder Reranking, Nested Context Builder, Strict Citation Validation, Semantic Cache). Tuy nhiên, sau nhiều chu kỳ phát triển liên tục, mã nguồn backend đang tồn đọng các vấn đề về kiến trúc, độ trùng lặp và tính tối ưu:
1. **Mã nguồn mồ côi (Dead code):** File `backend/app/services/rag.py` (173 dòng) chứa mã nguồn FAISS và context builder cũ không còn được import hay sử dụng ở bất kỳ đâu trong codebase, gây nhầm lẫn nghiêm trọng về kiến trúc với `pipeline.py`.
2. **Trùng lặp code điều phối nghiêm trọng:** Tại `backend/app/api/chat.py`, hai endpoint `POST /chat` (non-streaming) và `POST /chat/stream` (streaming) lặp lại hơn 150 dòng logic giống hệt nhau (chuẩn bị chat history, query rewriting, kiểm tra semantic cache, gọi retrieval, chuẩn bị context, validate trích dẫn, lưu cache, persist turn, gọi memory summarizer). Điều này làm tăng độ phức tạp và tiềm ẩn rủi ro lệch pha logic (desync).
3. **Các lỗi tiềm ẩn & mã hóa:** Lỗi chuỗi Mojibake tiếng Việt tại `backend/app/services/llm.py` dòng 338, điều kiện rẽ nhánh lặp lại trong `delete_session`, và cảnh báo `DeprecationWarning` do dùng cú pháp cũ `@application.on_event("startup")` trong FastAPI.
4. **Các điểm chưa tối ưu hiệu năng (Micro-optimizations):** Thuật toán sinh vector thưa (sparse vector) trong `sparse_vector.py` thực hiện quét danh sách tuyến tính $O(N)$ khi đụng độ băm thay vì dùng bảng băm $O(1)$; hàm `retrieve` và `aretrieve` trong `pipeline.py` gọi phản xạ `inspect.signature` trên mọi turn chat thay vì cache hoặc chuẩn hóa interface.

Cần một đợt tái cấu trúc, dọn dẹp và tối ưu hóa toàn diện để đưa backend RAG pipeline về trạng thái tinh gọn, sáng sủa, dễ bảo trì và vận hành với hiệu năng cao nhất.

## What Changes

- **Dọn dẹp mã nguồn thừa (Dead Code Removal):**
  - Xóa bỏ file mồ côi `backend/app/services/rag.py`.
  - Dọn dẹp các biến toàn cục trống và logic trùng lặp trong `backend/app/services/vectorstore.py`, chuẩn hóa việc gọi pipeline trực tiếp từ `api/documents.py`.
- **Tái cấu trúc bộ điều phối RAG trong `backend/app/api/chat.py`:**
  - Trích xuất logic dùng chung thành các module/helper điều phối rõ ràng (`RAGTurnManager` hoặc pipeline workflow helpers):
    - Khâu chuẩn bị (`prepare_turn_context`): Tóm tắt ngữ cảnh session, cửa sổ trượt chat history, query rewriting, kiểm tra semantic cache hit.
    - Khâu hoàn tất (`finalize_turn`): Xác thực trích dẫn `<cite id="...">`, cập nhật semantic cache, lưu trữ turn tuần tự vào PostgreSQL, kích hoạt tóm tắt bộ nhớ bất đồng bộ.
  - Thu gọn `chat_endpoint` và `chat_stream_endpoint` về đúng trách nhiệm nhận request, kích hoạt pipeline và stream/trả kết quả HTTP.
- **Sửa lỗi mã hóa & logic (Bug Fixes):**
  - Khắc phục lỗi Mojibake tiếng Việt tại `backend/app/services/llm.py`: chuyển `KhÃ´ng cÃ³ LLM provider...` thành `"Không có LLM provider nào khả dụng. Hãy kiểm tra cấu hình provider và API key."`.
  - Loại bỏ khối kiểm tra lặp `if not session_id or session_id == "unknown"` trong hàm `delete_session` của `api/chat.py`.
  - Hiện đại hóa startup event trong `backend/app/main.py`: chuyển `@application.on_event("startup")` sang async context manager `lifespan(app: FastAPI)` chuẩn FastAPI.
- **Tối ưu hóa hiệu năng (Performance Optimizations):**
  - Cải tiến `SparseVectorGenerator` (`backend/app/services/sparse_vector.py`): sử dụng map dictionary `{index: value}` để xử lý collision trong $O(1)$, loại bỏ thao tác quét tuyến tính `if index in indices:` và `indices.index(index)`.
  - Tối ưu hóa reflection trong `backend/app/services/pipeline.py`: loại bỏ `inspect.signature` trong hot-path của `retrieve` và `aretrieve`, chuẩn hóa interface nhận `api_key` hoặc cache cờ tham số lúc khởi tạo.

## Capabilities

### New Capabilities
- `rag-pipeline-orchestration`: Cung cấp tầng điều phối RAG thống nhất, tách bạch rõ ràng giữa xử lý HTTP controller và luồng nghiệp vụ RAG đa bước.

### Modified Capabilities
- `retrieval-persistence`: Làm sạch và tối ưu hóa các module search/sparse vector, loại bỏ các file mồ côi và phụ thuộc vòng.
- `strict-citation`: Giữ nguyên tính năng kiểm tra tính toàn vẹn của trích dẫn nhưng tích hợp vào quy trình hoàn tất turn tập trung.

## Impact
- **Backend:** Giảm hơn 250 dòng code trùng lặp và code chết; cấu trúc `api/chat.py` sáng sủa, dễ đọc; loại bỏ các cảnh báo deprecation khi khởi động server.
- **Hiệu năng:** Tốc độ tạo sparse vector và thời gian xử lý mỗi turn chat giảm bớt overhead introspection.
- **Tính ổn định:** Toàn bộ 124 tests hiện hữu tiếp tục pass 100%, bảo toàn nguyên vẹn hành vi và contracts với Frontend.
