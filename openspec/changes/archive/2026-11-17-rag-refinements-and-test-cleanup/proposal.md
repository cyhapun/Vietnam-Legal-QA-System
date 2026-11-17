# Proposal: RAG Pipeline Refinements and Test Suite Cleanup

## Why

Sau khi hệ thống RAG đã được tinh gọn và chuẩn hóa tầng suy luận hoàn toàn trên Google AI Studio, quá trình vận hành thực tế ghi nhận 4 điểm nghẽn và dư thừa cần tiếp tục hoàn thiện:

1. **Trải nghiệm tiêu đề phiên chat thô sơ (Primitive Chat Titles):** Hiện tại Frontend gán tiêu đề cho cuộc trò chuyện mới bằng cách cắt thô 40 ký tự đầu tiên của tin nhắn (`userText.substring(0, 40)`). Cách làm này khiến tiêu đề phiên chat ở thanh Sidebar bị cụt, lủng củng và chứa các đại từ xã giao thừa thãi (ví dụ: *"Bạn ơi cho mình hỏi theo quy định mới..."*). Trong khi đó, `LLMRewriter` đã đọc và hiểu toàn diện bản chất câu hỏi của người dùng ở lượt đầu tiên nhưng chưa được tận dụng để tạo ra một tiêu đề súc tích.
2. **Cơ chế cắt tỉa Token bóp méo bối cảnh pháp lý (`compact_builder`):** Trong `_build_context_with_budget`, khi tổng token của Top căn cứ pháp lý vượt ngưỡng ngân sách (`CONTEXT_TOKEN_BUDGET`), hệ thống tự động fallback sang `build_compact`. Phương thức này lược bỏ toàn bộ các điều luật dẫn chiếu chéo (Cấp 1, Cấp 2) và tước bỏ định dạng phân cấp của mọi tài liệu để cố nhồi nhét tài liệu. Việc này làm suy giảm chất lượng lập luận của các điều luật quan trọng nhất (Rank 1, Rank 2). Cần thay thế bằng cơ chế **Tail Document Pruning thuần túy**: Giữ nguyên vẹn 100% cấu trúc nested context cho các tài liệu hàng đầu và lần lượt loại bỏ các chunk có điểm xếp hạng thấp nhất ở cuối bảng xếp hạng (Rank 5, Rank 4,...) cho đến khi thỏa mãn ngân sách.
3. **Phễu ứng viên Retrieval chưa tối ưu độ phủ (Recall):** Mặc định `RETRIEVER_CANDIDATE_K` đang để ở mức 10. Với những câu hỏi pháp lý phức tạp liên quan đến nhiều nghị định, thông tư hoặc điều khoản viện dẫn chéo, phễu 10 ứng viên có nguy cơ bỏ sót các căn cứ tiềm năng trước khi đưa vào Cross-Encoder Reranker. Cần cố định `RETRIEVER_CANDIDATE_K = 20` để Reranker có đủ không gian 20 ứng viên tinh tuyển ra Top 5 căn cứ sát nhất.
4. **Phình to và phân mảnh bộ Test (`backend/tests/` Bloat):** Bộ unit test backend hiện tại chứa tới 17 file với 128 tests (gần 2.300 dòng code), trong đó có rất nhiều test rác, test legacy không còn giá trị (FAISS fallback khi Qdrant sập, test mode browser cũ, test đọc file requirements.txt, test script offline evaluation, test kiểm tra batch_size=0, v.v.). Cần xóa mạnh tay các file test thừa thãi, tái cấu trúc thành 5 file test cốt lõi tinh gọn, tập trung bảo vệ đúng các luồng nghiệp vụ sống còn của hệ thống.

## What Changes

- **Rewriter tự động sinh tiêu đề (Title Generation) ở lượt đầu tiên:**
  - Bổ sung trường `title: Optional[str] = None` vào `RewriteResult` và cập nhật System Prompt của `LLMRewriter`.
  - Nếu `Conversation History` rỗng hoặc là lượt chat đầu tiên, LLM sinh ra một tiêu đề tiếng Việt ngắn gọn (3-6 từ) tóm tắt chủ đề pháp lý (ví dụ: *"Điều kiện kinh doanh BĐS"*, *"Thủ tục cấp Giấy chứng nhận quyền sử dụng đất"*). Nếu là lượt tiếp theo, `title` trả về `null`.
  - Luồng truyền tải:
    - Streaming (`/chat/stream`): Bắn sự kiện SSE `event: title` (dạng `{"type": "title", "title": ...}`) ngay khi phân tích xong câu hỏi để Frontend cập nhật Sidebar tức thì.
    - Non-streaming (`/chat`): Trả về trường `sessionTitle` trong `ChatResponse`.
    - Persistence: Lưu tiêu đề thông minh này vào bảng `chat_sessions` trong PostgreSQL qua `ensure_session_exists` / `update_session_title`.
  - Frontend: `ChatInterface.tsx` lắng nghe sự kiện `type === 'title'` và gọi `updateSessionTitle(event.title)`.
- **Cắt tỉa Token theo cơ chế loại bỏ chunk có điểm thấp nhất (Tail Chunk Pruning):**
  - Tái cấu trúc `_build_context_with_budget(docs, token_budget)` trong `pipeline.py`: Bỏ hoàn toàn fallback `build_compact`.
  - Giữ nguyên cấu trúc Nested Context chuẩn (kèm dẫn chiếu chéo C1, C2).
  - Khi tổng token vượt `token_budget`: Lần lượt loại bỏ tài liệu ở vị trí cuối cùng ($doc_k, doc_{k-1}, \dots$) tương ứng với điểm Reranker thấp nhất cho đến khi tổng số token thỏa mãn budget (hoặc chỉ còn lại chunk Rank 1).
- **Cố định lấy Top 20 Candidates:**
  - Cập nhật `.env` và `.env.example`: `RETRIEVER_CANDIDATE_K=20`.
  - Cập nhật mặc định trong `backend/app/config.py`: `RETRIEVER_CANDIDATE_K = int(os.getenv("RETRIEVER_CANDIDATE_K", "20"))`.
  - Đảm bảo Hybrid Search (Dense BGE-M3 + Sparse BM25 + RRF) luôn gom 20 ứng viên hàng đầu trước khi chuyển sang Cross-Encoder Reranker.
- **Xóa mạnh tay và Tinh gọn bộ Test Suite:**
  - Xóa bỏ 12 file test legacy và fixtures thừa thãi trong `backend/tests/`:
    `test_local_models_real.py`, `test_local_model_config_validation.py`, `test_qdrant_faiss_fallback.py`, `test_legal_quality_evaluation.py`, `fixtures/`, `test_pipeline_timing.py`, `test_deployment_runtime_profiles.py`, `test_local_embedding_runtime.py`, `test_local_reranker_runtime.py`, `test_pipeline_lazy_init.py`, `test_pipeline_reranker_runtime.py`, `test_storage_schema_bootstrap.py`, `test_storage_dimension_config.py`.
  - Tái lập và giữ lại 5 file test cốt lõi (~25-30 test case):
    1. `test_pipeline.py`: Kiểm thử luồng pipeline hợp nhất (Rewriter sinh title, Candidate K = 20, Reranker Top 5, Cắt tỉa chunk thấp nhất khi vượt budget).
    2. `test_llm_google_fallback.py`: Kiểm thử chuyển đổi API key và model dự phòng trên Google AI Studio.
    3. `test_answer_validation.py`: Kiểm thử bóc tách trích dẫn `<cite>`, loại bỏ ID ảo giác và an toàn pháp lý.
    4. `test_chat_api.py`: Kiểm thử endpoint `/chat` và `/chat/stream` SSE (nhận event title, context, token, done), lưu trữ PostgreSQL.
    5. `test_health_readiness.py`: Kiểm thử endpoint `/health` và `/ready`.

## Capabilities

### New Capabilities
- `chat-session-smart-title`: Khả năng tự động phân tích chủ đề câu hỏi đầu tiên bằng LLM Rewriter để sinh tiêu đề tiếng Việt súc tích (3-6 từ) và đẩy về giao diện thời gian thực qua SSE.
- `tail-chunk-token-pruning`: Thuật toán cắt tỉa ngữ cảnh tuân thủ ngân sách token theo nguyên lý bảo tồn tài liệu quan trọng nhất (Top Rank) và loại bỏ dần các tài liệu xếp hạng thấp nhất (Tail/Lowest-Ranked Chunks), duy trì nguyên vẹn cấu trúc dẫn chiếu chéo sâu.

### Modified Capabilities
- `retrieval-candidate-pool`: Mở rộng và cố định số lượng ứng viên sơ bộ lên Top 20 (`candidate_k = 20`) cho phễu Reranking.
- `backend-test-suite`: Tinh gọn test suite backend từ 17 file xuống 5 file cốt lõi, loại bỏ hoàn toàn các test mock thừa thãi.

## Impact
- **Trải nghiệm người dùng (UX):** Danh sách lịch sử chat ở thanh Sidebar hiển thị tiêu đề chuyên nghiệp, phản ánh chính xác nội dung pháp lý ngay sau lượt gửi đầu tiên.
- **Độ chính xác pháp lý (Accuracy & Grounding):** Loại bỏ tình trạng các điều luật quan trọng nhất bị tước bỏ điều khoản viện dẫn chéo do cơ chế compact context, đồng thời mở rộng phễu tìm kiếm lên 20 candidate giúp tăng độ phủ Recall.
- **Tốc độ và Bảo trì (Developer Experience):** Bộ test suite chạy siêu nhanh (< 2 giây), code gọn gàng, loại bỏ các file kiểm thử mồ côi.
