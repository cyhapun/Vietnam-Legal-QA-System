# Tasks: Pure Google AI Studio Fallback & Minimal Pipeline Configuration

## 1. Tái Cấu Trúc Tầng Suy Luận LLM Backend (llm.py & provider_registry.py)
- [x] 1.1 Xây dựng hàm `parse_google_api_keys()` trong `backend/app/services/llm.py` để phân giải `GOOGLE_API_KEYS` (dạng comma-separated) hoặc `GOOGLE_API_KEY`, tự động khử trùng lặp và loại bỏ khoảng trắng thừa.
- [x] 1.2 Triển khai thuật toán Fallback ưu tiên đổi Key trước (`build_google_llm_chain`): Duyệt toàn bộ các API Key trên Model chính trước khi hạ cấp sang các Model phụ trong `GOOGLE_FALLBACK_MODELS`.
- [x] 1.3 Loại bỏ toàn bộ code mồ côi và phân nhánh không còn sử dụng trong `llm.py`: `_resolve_provider_models`, `_legacy_get_llm`, `INFERENCE_STRATEGY`, `HUGGINGFACE_PROVIDER`, `OLLAMA_PROVIDER`.
- [x] 1.4 Tinh giản `backend/app/services/provider_registry.py`: Chỉ giữ lại provider `google`, danh sách model `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, `gemini-2.5-flash`, và loại bỏ registry của Ollama/HuggingFace.

## 2. Chuẩn Hóa Rewriter & Memory Manager Dùng Google AI Studio
- [x] 2.1 Cập nhật `backend/app/services/rewriting/llm_rewriter.py`: Bỏ cấu hình provider `ollama` và model `qwen2.5:1.5b`, sử dụng trực tiếp `get_llm(role=REWRITER_ROLE)` trên nền tảng Google Gemini.
- [x] 2.2 Cập nhật `backend/app/services/memory_manager.py`: Thay thế chuỗi hardcode `model_name="qwen2.5:1.5b"` bằng `get_llm(role=SUMMARIZER_ROLE)`.
- [x] 2.3 Đặt mặc định `PIPELINE_REWRITER="llm"` trong `backend/app/config.py` để tính năng viết lại câu hỏi pháp luật luôn được kích hoạt.

## 3. Tinh Gọn Cấu Hình Backend (config.py & .env)
- [x] 3.1 Dọn dẹp `backend/app/config.py`: Loại bỏ các biến mồ côi (FAISS, Ollama, Tracking files, các cờ boolean không còn tác dụng), gán mặc định an toàn trong code cho các tham số vi mô (device, batch size, length, weights).
- [x] 3.2 Rút gọn file `.env` từ 155 dòng xuống ~25 dòng chỉ chứa các thông số môi trường thực sự cần thiết (Dịch vụ, Google Keys/Models, DB, Vector DB, RAG core params).
- [x] 3.3 Cập nhật tương ứng cho `.env.example` để người phát triển mới dễ dàng thiết lập môi trường.

## 4. Đồng Bộ Hóa Giao Diện Người Dùng (Frontend)
- [x] 4.1 Cập nhật `frontend/lib/constants.ts`: Loại bỏ hoàn toàn Ollama và HuggingFace khỏi `AI_PROVIDERS` và `AI_MODELS`, chỉ giữ lại Google AI Studio với các model Gemini.
- [x] 4.2 Cập nhật `frontend/components/chat/ProviderSelector.tsx` để hiển thị selector phù hợp với danh sách model Google mới.
- [x] 4.3 Cập nhật các kịch bản kiểm thử frontend (`verify-ai-models.mjs`, `verify-inference-settings.mjs`) để khớp với danh sách model Google chuẩn hóa.

## 5. Kiểm Thử, Cập Nhật Test Suite & Xác Minh Thực Tế
- [x] 5.1 Cập nhật unit tests trong `backend/tests/test_llm_google_fallback.py` và `backend/tests/test_runtime_inference_config.py` để kiểm thử logic Multi-Key và Multi-Model Fallback mới.
- [x] 5.2 Chạy toàn bộ test suite backend `PYTHONPATH=. .venv/bin/pytest tests/` đảm bảo 100% tests pass.
- [x] 5.3 Chạy toàn bộ test suite frontend (`npm run verify:models`, `npm run verify:inference-settings`, `npm run verify:chat-ux`).
- [x] 5.4 Khởi động lại backend server, kiểm tra `/health`, `/readiness`, và gửi request thử nghiệm đến `/chat` và `/chat/stream` để kiểm tra trực tiếp luồng phản hồi và trích dẫn `<cite>`.
