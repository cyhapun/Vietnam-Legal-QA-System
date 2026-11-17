# Tasks: RAG Pipeline Refinements and Test Suite Cleanup

## 1. Sinh Tiêu Đề Thông Minh (Smart Title Generation)
- [x] 1.1 Cập nhật `backend/app/services/rewriting/base.py`: Thêm trường `title: Optional[str] = None` vào model `RewriteResult`.
- [x] 1.2 Cập nhật `backend/app/services/rewriting/llm_rewriter.py`: Bổ sung chỉ dẫn System Prompt yêu cầu LLM sinh tiêu đề tiếng Việt súc tích (3-6 từ) ở lượt chat đầu tiên (khi history rỗng), và trả về `null` ở các lượt sau; trích xuất `title` an toàn từ JSON output.
- [x] 1.3 Cập nhật `backend/app/services/chat_orchestrator.py`:
  - Chuẩn hóa `rewrite_query` tiếp nhận và trả về `title`.
  - Bổ sung `session_title` vào `PreparedTurnContext`.
  - Phát sự kiện SSE `event: title` trong luồng streaming `/chat/stream` và bổ sung `sessionTitle` vào response của `/chat`.
  - Cập nhật hàm `persist_turn` để đồng bộ `session_title` vào bảng `chat_sessions` trong PostgreSQL qua `update_session_title`.
- [x] 1.4 Cập nhật `frontend/components/chat/ChatInterface.tsx`:
  - Bổ sung xử lý sự kiện SSE `type === 'title'` để gọi `updateSessionTitle(event.title)`, cập nhật thanh Sidebar ngay lập tức.
  - Xử lý `data.sessionTitle` trong luồng non-streaming response.

## 2. Cắt Tỉa Token Theo Thứ Hạng (Tail Chunk Pruning)
- [x] 2.1 Tái cấu trúc hàm `_build_context_with_budget(docs, token_budget)` trong `backend/app/services/pipeline.py`:
  - Loại bỏ hoàn toàn fallback `build_compact`.
  - Áp dụng thuật toán Tail Document Pruning: Khi tổng số token ước lượng vượt `token_budget`, lần lượt loại bỏ chunk ở cuối danh sách (chunk có điểm xếp hạng thấp nhất) cho đến khi thỏa mãn ngân sách hoặc chỉ còn lại chunk Rank 1.
  - Bổ sung log chi tiết các chunk bị loại bỏ và số lượng token ước lượng.

## 3. Cố Định Top 20 Candidates Cho Retrieval
- [x] 3.1 Cập nhật cấu hình môi trường `.env` và `.env.example`: Đặt cố định `RETRIEVER_CANDIDATE_K=20`.
- [x] 3.2 Cập nhật giá trị mặc định trong `backend/app/config.py`: `RETRIEVER_CANDIDATE_K = int(os.getenv("RETRIEVER_CANDIDATE_K", "20"))`.
- [x] 3.3 Đảm bảo các hàm truy xuất trong `pipeline.py` và `chat_orchestrator.py` sử dụng chuẩn `candidate_k = 20` trước khi chuyển sang Cross-Encoder Reranker.

## 4. Dọn Dẹp Mạnh Tay & Tái Cấu Trúc Bộ Test Suite
- [x] 4.1 Xóa bỏ 12 file test legacy/bloat và thư mục fixtures trong `backend/tests/`:
  - `test_local_models_real.py`
  - `test_local_model_config_validation.py`
  - `test_qdrant_faiss_fallback.py`
  - `test_legal_quality_evaluation.py` & thư mục `fixtures/`
  - `test_pipeline_timing.py`
  - `test_deployment_runtime_profiles.py`
  - `test_local_embedding_runtime.py`
  - `test_local_reranker_runtime.py`
  - `test_pipeline_lazy_init.py`
  - `test_pipeline_reranker_runtime.py`
  - `test_storage_schema_bootstrap.py`
  - `test_storage_dimension_config.py`
- [x] 4.2 Xây dựng file test chuẩn hóa `backend/tests/test_pipeline.py`:
  - Kiểm thử Rewriter sinh `title` ở lượt đầu và trả về `None` khi có history.
  - Kiểm thử Retrieval cố định `candidate_k = 20`.
  - Kiểm thử Reranker Top 5.
  - Kiểm thử Tail Chunk Pruning loại bỏ chunk điểm thấp nhất khi vượt budget.
- [x] 4.3 Tái cấu trúc và tinh giản `backend/tests/test_chat_api.py` (từ `test_chat_fallback.py`):
  - Kiểm thử `/chat` và `/chat/stream` (nhận đầy đủ các event SSE: `title`, `context`, `token`, `done`).
  - Kiểm thử lưu trữ hội thoại vào PostgreSQL.
- [x] 4.4 Kiểm tra và hoàn thiện các file test còn lại: `test_llm_google_fallback.py`, `test_answer_validation.py`, `test_health_readiness.py`.

## 5. Xác Minh Thực Tế & Đảm Bảo Chất Lượng
- [x] 5.1 Chạy toàn bộ test suite backend: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/` (100% passed, thời gian chạy < 2s).
- [x] 5.2 Chạy toàn bộ kiểm thử frontend: `cd frontend && node scripts/verify-chat-ux.mjs`.
- [x] 5.3 Khởi động lại dịch vụ backend, thực hiện truy vấn thử nghiệm end-to-end trên trình duyệt/cURL để xác nhận tiêu đề mới hiển thị mượt mà trên UI.
