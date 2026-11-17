# Proposal: Pure Google AI Studio Fallback & Minimal Pipeline Configuration

## Why

Hệ thống tư vấn pháp luật hiện tại đã được tối ưu hóa về luồng xử lý RAG, tuy nhiên cấu hình và tầng suy luận LLM vẫn đang tồn đọng các vấn đề phức tạp và dư thừa nghiêm trọng:
1. **Phân mảnh Provider & Cơ chế Fallback lai tạp:** Tầng LLM (`backend/app/services/llm.py` và `provider_registry.py`) đang phải duy trì đồng thời 3 hệ sinh thái: Google AI Studio, HuggingFace Router (Novita, Qwen, DeepSeek, Llama), và Ollama cục bộ. Việc này dẫn đến hàng trăm dòng code điều hướng phức tạp (`_resolve_provider_models`, `INFERENCE_STRATEGY`, `_legacy_get_llm`), trong khi trên thực tế toàn bộ hệ thống đã chuẩn hóa chất lượng câu trả lời trên các dòng mô hình Google Gemini.
2. **Nguy cơ lỗi tiềm ẩn do phụ thuộc ngầm vào Ollama:** Hai thành phần quan trọng của pipeline là `memory_manager.py` (tóm tắt lịch sử hội thoại) và `llm_rewriter.py` (viết lại & phân tích câu hỏi) vẫn đang hardcode gọi `qwen2.5:1.5b` qua Ollama. Khi môi trường không cài đặt hoặc không chạy Ollama daemon, các thành phần này sẽ ném cảnh báo hoặc lỗi.
3. **Thiếu cơ chế xoay vòng Key và Model nội bộ Google:** Khi chỉ sử dụng 1 khóa API Google duy nhất, hệ thống dễ rơi vào trạng thái tê liệt khi gặp lỗi `429 Too Many Requests` (hết quota / rate limit của tier miễn phí) hoặc `503 Service Unavailable` khi một model tạm thời quá tải. Cần một cơ chế xoay vòng thông minh: **ưu tiên đổi API Key trước**, sau đó mới **đổi sang model dự phòng**.
4. **Phình to cấu hình (Configuration Bloat):** File `.env` đang chứa hơn 155 dòng với hàng loạt biến cấu hình mồ côi (FAISS legacy, Ollama, các tham số sleep/retry/weight vi mô) gây khó khăn cho việc triển khai, bàn giao và bảo trì.
5. **Đồng bộ hóa Frontend:** Giao diện người dùng vẫn còn selector hiển thị các model Ollama và HuggingFace cũ, cần được đồng bộ hóa hoàn toàn để chỉ hiển thị các model Google Gemini được hỗ trợ.

## What Changes

- **Hợp nhất Tầng Suy luận 100% về Google AI Studio:**
  - Loại bỏ hoàn toàn các provider Ollama, HuggingFace Router và Novita ra khỏi `llm.py` và `provider_registry.py`.
  - Toàn bộ các tác vụ LLM (`answer`, `rewriter`, `summarizer`) sử dụng chung pool Google AI Studio.
- **Xây dựng Chuỗi Fallback Đa Tầng (Multi-Key & Multi-Model):**
  - Hỗ trợ nạp danh sách API Key qua `GOOGLE_API_KEYS` (chuỗi phân cách bằng dấu phẩy) hoặc `GOOGLE_API_KEY`.
  - Thiết lập model chính (`GOOGLE_MODEL="gemini-3.1-flash-lite"`) và danh sách model dự phòng (`GOOGLE_FALLBACK_MODELS="gemini-2.5-flash-lite,gemini-2.5-flash"`).
  - Thuật toán Fallback: **Ưu tiên đổi Key trước** trên cùng một model để tối đa hóa chất lượng câu trả lời:
    `(Model A, Key 1)` $\rightarrow$ `(Model A, Key 2)` $\rightarrow$ `(Model B, Key 1)` $\rightarrow$ `(Model B, Key 2)`.
  - Tận dụng `with_fallbacks()` của LangChain để tự động bắt các lỗi HTTP 429, 503 và chuyển tiếp trong suốt.
- **Kích hoạt Mặc định Query Rewriter:**
  - Chuyển `PIPELINE_REWRITER` sang `"llm"` làm mặc định.
  - Cập nhật `LLMRewriter` và `summarize_session` dùng trực tiếp Google LLM với cơ chế fallback tương tự.
- **Tối giản Hóa Cấu hình (`config.py` & `.env`):**
  - Xóa bỏ toàn bộ các biến mồ côi: `OLLAMA_*`, `FAISS_*`, `TRACKING_FILE`, `INFERENCE_STRATEGY`, `ENABLE_GOOGLE_FALLBACK`, `RETRIEVER_FETCH_K`, `RETRIEVER_LAMBDA_MULT`.
  - Chuyển các tham số vi mô (batch sizes, max lengths, weights) thành hằng số mặc định tối ưu sẵn trong mã nguồn.
  - Thu gọn file `.env` xuống khoảng 20-25 dòng cốt lõi thực sự cần thiết.
- **Đồng bộ Giao diện Frontend:**
  - Cập nhật `frontend/lib/constants.ts` và `ProviderSelector.tsx` chỉ hiển thị các model Google AI Studio: `gemini-3.1-flash-lite` (mặc định), `gemini-2.5-flash-lite`, `gemini-2.5-flash`.
  - Cập nhật các script kiểm thử frontend tương ứng.

## Capabilities

### New Capabilities
- `google-multi-key-fallback`: Cho phép khai báo nhiều API Key của Google AI Studio và tự động luân chuyển khi một key bị chạm ngưỡng rate-limit/quota.
- `google-multi-model-fallback`: Cho phép định nghĩa danh sách các model dự phòng và tự động suy giảm bậc dịch vụ an toàn khi model chính gặp sự cố quá tải.

### Modified Capabilities
- `llm-runtime`: Tối giản hóa tầng kết nối LLM, loại bỏ các phân nhánh Ollama và HuggingFace.
- `system-configuration`: Chuẩn hóa file `.env` và `config.py` tinh gọn tối đa.
- `agentic-query-rewriter`: Luôn hoạt động mặc định dựa trên Google Gemini thay vì Ollama.
- `frontend-model-selector`: Giao diện trực quan chỉ hiển thị các mô hình Google AI Studio khả dụng.

## Impact
- **Độ tin cậy & Sẵn sàng cao:** Loại bỏ hoàn toàn nguy cơ sập dịch vụ do 1 API key hết quota miễn phí hoặc 1 model Gemini bảo trì.
- **Đơn giản hóa Triển khai:** File cấu hình `.env` gọn gàng, người dùng chỉ cần điền API key Google và thông số cơ sở dữ liệu là hệ thống chạy ngay lập tức.
- **Bảo trì Mã nguồn:** Giảm bớt hàng trăm dòng code phân nhánh rườm rà, loại bỏ triệt để các cảnh báo không tìm thấy Ollama/HuggingFace token.
