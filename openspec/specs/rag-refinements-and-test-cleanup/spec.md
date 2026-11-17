# rag-refinements-and-test-cleanup Specification

## Purpose
Nâng cao chất lượng trải nghiệm người dùng và độ chính xác của ngữ cảnh pháp lý bằng cách:
1. Tự động sinh tiêu đề tiếng Việt thông minh (3-6 từ) ở lượt đầu tiên bằng `LLMRewriter` và đẩy qua SSE về Frontend thời gian thực.
2. Chuẩn hóa cơ chế cắt tỉa token theo nguyên lý Tail Chunk Pruning (loại bỏ dần các chunk có điểm thấp nhất ở cuối bảng xếp hạng khi vượt ngân sách, bảo toàn nguyên vẹn 100% Nested Context của các tài liệu Top đầu).
3. Cố định lấy Top 20 candidates (`RETRIEVER_CANDIDATE_K = 20`) ở tầng tìm kiếm lai (Hybrid Search) trước khi chuyển vào Cross-Encoder Reranker.
4. Xóa bỏ dứt điểm 12 file test legacy/bloat trong `backend/tests/` và tái cấu trúc thành 5 file test cốt lõi tinh gọn, chạy siêu tốc (< 2 giây).

## Requirements

### Requirement: Smart Title Generation on First Turn
Hệ thống SHALL tự động sinh ra một tiêu đề tiếng Việt ngắn gọn (3-6 từ) tóm tắt chủ đề pháp lý của cuộc trò chuyện trong lượt chat đầu tiên (`turn_count == 0` hoặc history rỗng) thông qua `LLMRewriter`, sau đó truyền về Frontend qua SSE và lưu vào PostgreSQL.

#### Scenario: First turn legal query generates concise title
- **WHEN** người dùng bắt đầu một cuộc hội thoại mới và gửi câu hỏi pháp lý đầu tiên (ví dụ: *"Tôi muốn mua mảnh đất chưa có sổ đỏ thì cần lưu ý gì?"*)
- **THEN** `LLMRewriter` phân tích câu hỏi và trả về `RewriteResult` chứa trường `title` tiếng Việt súc tích (ví dụ: *"Điều kiện mua đất chưa có sổ"*).
- **AND THEN** endpoint streaming `/chat/stream` phát ra sự kiện SSE `event: title` với payload `{"type": "title", "title": "..."}` ngay ở giai đoạn phân tích.
- **AND THEN** Frontend nhận sự kiện và cập nhật thanh Sidebar với tiêu đề thông minh thay vì chuỗi cắt thô 40 ký tự.
- **AND THEN** tiêu đề này được lưu vào bảng `chat_sessions` trong PostgreSQL.

#### Scenario: Subsequent turns do not overwrite title
- **WHEN** người dùng gửi câu hỏi ở các lượt tiếp theo trong cùng một phiên chat (`len(messages) > 1` hoặc đã có history)
- **THEN** `LLMRewriter` trả về `title: null` (None).
- **AND THEN** hệ thống không ghi đè tiêu đề phiên chat đã được thiết lập trước đó.

---

### Requirement: Tail Chunk Token Pruning
Hệ thống SHALL thực hiện cắt tỉa ngữ cảnh tuân thủ ngân sách `CONTEXT_TOKEN_BUDGET` theo nguyên tắc bảo toàn tài liệu quan trọng nhất (Rank 1, Rank 2) và lần lượt loại bỏ các chunk ở cuối bảng xếp hạng (Tail / Lowest-Ranked Chunks) thay vì chuyển sang định dạng vắn tắt `compact_builder`.

#### Scenario: Nested context within token budget
- **WHEN** tổng số token ước lượng của toàn bộ danh sách tài liệu sau khi rerank $\le$ `CONTEXT_TOKEN_BUDGET`
- **THEN** toàn bộ tài liệu cùng các điều luật dẫn chiếu chéo (Cấp 1, Cấp 2) được giữ nguyên vẹn trong bối cảnh cung cấp cho LLM.

#### Scenario: Context exceeds budget drops lowest-ranked chunks
- **WHEN** tổng số token ước lượng của tập tài liệu vượt quá `CONTEXT_TOKEN_BUDGET`
- **THEN** hệ thống loại bỏ dần tài liệu ở vị trí cuối cùng trong danh sách (chunk có điểm Reranker thấp nhất: Rank 5, rồi Rank 4,...).
- **AND THEN** tài liệu Rank 1 quan trọng nhất luôn được bảo toàn 100% cấu trúc nested context.
- **AND THEN** hệ thống không gọi `build_compact` làm suy giảm thông tin dẫn chiếu chéo của tài liệu hàng đầu.

---

### Requirement: Fixed Top 20 Candidates for Retrieval Funnel
Hệ thống SHALL cấu hình và cố định số lượng ứng viên truy xuất sơ bộ ở mức Top 20 (`RETRIEVER_CANDIDATE_K = 20`) tại cấu hình hệ thống và tầng truy xuất lai (Hybrid Search).

#### Scenario: Hybrid search candidate retrieval
- **WHEN** hệ thống thực thi truy xuất tài liệu cho truy vấn pháp lý
- **THEN** tầng Qdrant Hybrid Search (Dense BGE-M3 + Sparse BM25 + RRF) thu thập 20 ứng viên tiềm năng nhất.
- **AND THEN** danh sách 20 ứng viên này được chuyển trực tiếp vào Cross-Encoder Reranker để chấm điểm ngữ cảnh và chọn ra Top 5 căn cứ sát nhất.

---

### Requirement: Minimal and High-Value Test Suite
Hệ thống SHALL loại bỏ hoàn toàn các file test thừa thãi, mồ côi hoặc không phản ánh đúng kiến trúc hiện tại, duy trì 5 file test cốt lõi tinh gọn với thời gian thực thi dưới 2 giây.

#### Scenario: Clean backend test execution
- **WHEN** chạy lệnh `PYTHONPATH=. pytest` trong thư mục `backend/`
- **THEN** chỉ có 5 file test cốt lõi được thực thi: `test_pipeline.py`, `test_llm_google_fallback.py`, `test_answer_validation.py`, `test_chat_api.py`, `test_health_readiness.py`.
- **AND THEN** 100% test case pass thành công mà không có cảnh báo deprecation hoặc import lỗi từ các mô hình/fallback cũ.
