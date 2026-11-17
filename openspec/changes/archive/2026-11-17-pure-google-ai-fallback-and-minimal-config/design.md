# Design: Pure Google AI Studio Fallback & Minimal Pipeline Configuration

## 1. Overview & Architectural Goals

Mục tiêu thiết kế là chuyển đổi toàn diện tầng suy luận (Inference Layer) của VietLaw AI sang mô hình **Single-Provider, Multi-Key, Multi-Model**:
* **Single-Provider**: Chỉ sử dụng duy nhất Google AI Studio API qua chuẩn giao tiếp tương thích OpenAI (`https://generativelanguage.googleapis.com/v1beta/openai/`).
* **Multi-Key Fallback**: Hỗ trợ danh sách khóa API của Google, tự động xoay vòng khi một khóa bị lỗi `429 Too Many Requests` (Quota / Rate limit).
* **Multi-Model Fallback**: Tự động chuyển tiếp sang model thứ cấp (ví dụ `gemini-2.5-flash-lite`, `gemini-2.5-flash`) khi model chính (`gemini-3.1-flash-lite`) bị quá tải hoặc lỗi `503`.
* **Key-First Priority**: Ưu tiên thử toàn bộ danh sách API Key trên model chất lượng cao nhất trước khi hạ cấp sang model dự phòng.
* **Minimal Configuration**: Loại bỏ mọi biến cấu hình mồ côi (Ollama, FAISS, các tham số tuning nội bộ) khỏi `.env`, đưa file cấu hình về trạng thái tối giản nhất (~20-25 dòng).

---

## 2. Chuỗi Fallback: Thứ tự Ưu tiên (Key-First Priority)

### 2.1 Thuật toán xây dựng Fallback Chain

Giả sử hệ thống được cấu hình:
* **Models**: `[M1 (chính), M2 (dự phòng 1), M3 (dự phòng 2)]` (vd: `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, `gemini-2.5-flash`)
* **Keys**: `[K1, K2, K3]` (lấy từ biến `GOOGLE_API_KEYS` hoặc `GOOGLE_API_KEY`)

Thuật toán sinh danh sách LLM theo nguyên tắc **ưu tiên đổi Key trước**:

```
Bước 1: (M1, K1)  <-- LLM Chính (Primary)
Bước 2: (M1, K2)  <-- Fallback 1: Giữ model M1, đổi sang Key 2
Bước 3: (M1, K3)  <-- Fallback 2: Giữ model M1, đổi sang Key 3
Bước 4: (M2, K1)  <-- Fallback 3: Chuyển sang Model M2, bắt đầu lại với Key 1
Bước 5: (M2, K2)  <-- Fallback 4: Model M2, Key 2
Bước 6: (M2, K3)  <-- Fallback 5: Model M2, Key 3
Bước 7: (M3, K1)  <-- Fallback 6: Model M3, Key 1
...
```

### 2.2 Sơ đồ Luồng Thực Thi (Execution Flow)

```
                       Request từ Pipeline
                                │
                                ▼
                   ┌─────────────────────────┐
                   │   Tạo Primary LLM       │
                   │   Model M1 với Key K1   │
                   └────────────┬────────────┘
                                │
                                ▼
                   ┌─────────────────────────┐
                   │ Tạo Fallback Chain      │
                   │ [(M1, K2), (M1, K3),    │
                   │  (M2, K1), (M2, K2)...] │
                   └────────────┬────────────┘
                                │
                                ▼
                   ┌─────────────────────────┐
                   │ primary.with_fallbacks( │
                   │       fallback_chain)   │
                   └────────────┬────────────┘
                                │
                  Gọi .ainvoke() / .astream()
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
              Thành công                      Thất bại (429/503)
                 │                             │
                 ▼                             ▼
           Trả về kết quả             LangChain tự động bắt lỗi
                                      và chuyển sang fallback kế tiếp
```

### 2.3 Xử lý ngoại lệ trong LangChain
`ChatOpenAI.with_fallbacks()` trong LangChain tự động bắt các lỗi dẫn xuất từ `openai.RateLimitError` (HTTP 429), `openai.APIConnectionError`, `openai.InternalServerError` (HTTP 500, 503) và `openai.AuthenticationError` (nếu key sai hoặc bị thu hồi). Khi xảy ra các lỗi này, execution context tự động switch sang instance tiếp theo trong danh sách mà không ngắt luồng gọi của caller.

---

## 3. Tinh Gọn & Tái Cấu Trúc Các Module Backend

### 3.1 `backend/app/services/llm.py`
* **Loại bỏ**:
  * Các import và hằng số: `HUGGINGFACE_PROVIDER`, `OLLAMA_PROVIDER`, `INFERENCE_STRATEGY`, `_resolve_provider_models`, `_legacy_get_llm`.
  * Toàn bộ nhánh điều kiện xử lý HuggingFace Router và Ollama.
* **Thêm mới**:
  * Hàm `parse_google_api_keys()`: Đọc `GOOGLE_API_KEYS` (dạng comma-separated) hoặc `GOOGLE_API_KEY`, lọc các khoảng trắng và loại bỏ các key rỗng hoặc trùng lặp.
  * Hàm `get_google_chat_models()`: Đọc `GOOGLE_MODEL` và `GOOGLE_FALLBACK_MODELS` (dạng comma-separated).
  * Hàm `build_google_llm_chain(model_name, temperature, max_tokens, timeout)`: Xây dựng primary LLM và fallback chain theo thuật toán Key-first.
* **Cập nhật `get_llm()`**:
  * Trở thành hàm wrapper gọi `build_google_llm_chain()`.
  * Hỗ trợ role-based inference (`answer`, `rewriter`, `summarizer`) đồng nhất trên nền tảng Google.

### 3.2 `backend/app/services/provider_registry.py`
* Đơn giản hóa registry:
  * Chỉ duy trì `GOOGLE_PROVIDER = "google"`.
  * Khai báo danh sách các Google chat models được hỗ trợ: `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, `gemini-2.5-flash`.
  * Xóa bỏ `HUGGINGFACE_CHAT_MODELS` và `OLLAMA_CHAT_MODELS`.

### 3.3 `backend/app/services/rewriting/llm_rewriter.py`
* Xóa bỏ cấu hình mồ côi `PIPELINE_CONFIG.get("rewriter_model_provider", "ollama")` và `PIPELINE_CONFIG.get("rewriter_model_name", "qwen2.5:1.5b")`.
* Khởi tạo LLM cho rewriter thông qua `get_llm(role=REWRITER_ROLE)` (mặc định sử dụng Google AI Studio).

### 3.4 `backend/app/services/memory_manager.py`
* Trong hàm `summarize_session`, thay thế việc hardcode `model_name="qwen2.5:1.5b"` bằng việc gọi trực tiếp `get_llm(role=SUMMARIZER_ROLE)` (tự động kế thừa Google AI Studio và pool fallback).

### 3.5 `backend/app/config.py` & `.env`
* **Xóa bỏ các biến chết/thừa**:
  * `OLLAMA_BASE_URL`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_EMBEDDING_TIMEOUT`, `REWRITER_MODEL_PROVIDER`, `REWRITER_MODEL_NAME`.
  * `INFERENCE_STRATEGY`, `ENABLE_GOOGLE_FALLBACK`.
  * `FAISS_INDEX_PATH`, `ENABLE_FAISS_FALLBACK`, `TRACKING_FILE`, `EMBEDDED_FILES_PATH`, `RETRIEVER_FETCH_K`, `RETRIEVER_LAMBDA_MULT`.
* **Đặt mặc định an toàn trong code (không cần hiển thị ra `.env`)**:
  * `STORAGE_BACKEND = "qdrant_postgres"`
  * `PIPELINE_SEARCH = "hybrid"`
  * `PIPELINE_CHUNKING = "clause"`
  * `PIPELINE_CONTEXT_BUILDER = "nested"`
  * `PIPELINE_REWRITER = "llm"` (luôn bật query rewriter mặc định theo yêu cầu)
  * `EMBEDDING_DEVICE = "cpu"`, `RERANKER_DEVICE = "cpu"`
  * Các tham số batch size, max retries, timeout có giá trị mặc định tối ưu sẵn.
* **Cấu hình `.env` tối giản**:
  Chỉ giữ lại các biến cần thiết: Host, Google Keys/Models, Embedding/Reranking local paths, Database credentials (Postgres, Qdrant), và tham số RAG cơ bản (`RETRIEVER_K`, `RETRIEVER_CANDIDATE_K`, `CONTEXT_TOKEN_BUDGET`, `ENABLE_SEMANTIC_CACHE`).

---

## 4. Đồng Bộ Giao Diện Người Dùng (Frontend UI)

### 4.1 `frontend/lib/constants.ts`
* Đổi danh sách `AI_PROVIDERS`: Chỉ gồm duy nhất Google AI Studio (`{ id: 'google', name: 'Google AI Studio', requiresApiKey: true, deploymentSupported: true }`).
* Đổi danh sách `AI_MODELS`:
  ```typescript
  export const AI_MODELS: AIModel[] = [
    { id: 'gemini-3.1-flash-lite', provider: 'google', name: 'Gemini 3.1 Lite', fullName: 'Gemini 3.1 Flash-Lite' },
    { id: 'gemini-2.5-flash-lite', provider: 'google', name: 'Gemini 2.5 Lite', fullName: 'Gemini 2.5 Flash-Lite' },
    { id: 'gemini-2.5-flash', provider: 'google', name: 'Gemini 2.5 Flash', fullName: 'Gemini 2.5 Flash' },
  ];
  ```
* Model mặc định giữ nguyên: `DEFAULT_MODEL = 'gemini-3.1-flash-lite'`.

### 4.2 `frontend/components/chat/ProviderSelector.tsx`
* Hiển thị selector cho phép người dùng chọn giữa các model Google Gemini được hỗ trợ hoặc cố định thông tin model theo profile.

### 4.3 Cập nhật Scripts Kiểm Thử Frontend
* Cập nhật `frontend/scripts/verify-ai-models.mjs` và `frontend/scripts/verify-inference-settings.mjs` để kiểm tra danh sách model mới của Google.

---

## 5. Chiến Lược Kiểm Thử (Testing Strategy)

1. **Unit Tests cho Multi-Key & Multi-Model Fallback (`test_llm_google_fallback.py`)**:
   * Kiểm thử parse 1 key vs nhiều key (`key1,key2`).
   * Kiểm thử thứ tự chuỗi fallback: `Key 1 -> Key 2` trên Model 1, sau đó mới đến `Key 1 -> Key 2` trên Model 2.
   * Kiểm thử khi Key 1 gặp lỗi rate limit `429`, pipeline tự động chuyển sang Key 2 thành công.
2. **Unit Tests cho Runtime Inference Config (`test_runtime_inference_config.py`)**:
   * Xác nhận hệ thống chỉ chấp nhận provider `google` và từ chối các provider cũ không còn hỗ trợ (`ollama`, `huggingface`).
3. **End-to-End Regression Tests**:
   * Chạy lại toàn bộ test suite backend để đảm bảo không có bất kỳ component nào bị ảnh hưởng tiêu cực.
   * Kiểm tra live endpoints `/chat` và `/chat/stream` với Google AI Studio.
