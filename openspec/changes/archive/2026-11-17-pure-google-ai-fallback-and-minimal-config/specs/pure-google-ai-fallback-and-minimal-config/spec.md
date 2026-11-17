# pure-google-ai-fallback-and-minimal-config Specification

## Purpose
Quy tụ toàn bộ năng lực suy luận ngôn ngữ (LLM) của hệ thống về Google AI Studio duy nhất, loại bỏ hoàn toàn các provider phân mảnh (HuggingFace Router, Novita, Ollama) và cấu hình mồ côi (FAISS, Ollama); xây dựng cơ chế Fallback đa tầng ưu tiên đổi API Key trước rồi đổi Model sau; kích hoạt mặc định Query Rewriter trên nền tảng Google; và tối giản hóa file cấu hình `.env` về trạng thái gọn nhẹ, dễ vận hành.

## Requirements

### Requirement: Single-provider Google AI Studio inference
Hệ thống SHALL chỉ sử dụng Google AI Studio làm nhà cung cấp mô hình ngôn ngữ lớn (LLM) duy nhất cho tất cả các vai trò (`answer`, `rewriter`, `summarizer`), đồng thời từ chối hoặc loại bỏ các nhà cung cấp phân mảnh cũ (HuggingFace Router, Ollama).

#### Scenario: Requesting LLM without legacy providers
- **WHEN** hệ thống khởi tạo kết nối LLM cho bất kỳ vai trò nào (`answer`, `rewriter`, `summarizer`)
- **THEN** client LLM được tạo ra sử dụng base URL của Google AI Studio tương thích OpenAI.
- **AND THEN** không có bất kỳ kết nối nào được tạo đến Ollama hoặc HuggingFace Router.

#### Scenario: Rejecting obsolete legacy providers in runtime config
- **WHEN** client gửi cấu hình runtime chứa provider không phải `google` (như `ollama` hoặc `huggingface`)
- **THEN** hệ thống ném ngoại lệ validation lỗi cấu hình không được hỗ trợ.

---

### Requirement: Multi-key fallback with key-first priority
Hệ thống SHALL hỗ trợ tiếp nhận một hoặc nhiều khóa API Google (`GOOGLE_API_KEYS` hoặc `GOOGLE_API_KEY`) và tự động chuyển sang khóa tiếp theo khi khóa hiện tại gặp sự cố (HTTP 429 Too Many Requests / Quota Exceeded / Authentication Error). Thứ tự xoay vòng bắt buộc phải ưu tiên thử toàn bộ danh sách khóa trên cùng một mô hình trước khi hạ cấp sang mô hình khác.

#### Scenario: Single API key configured
- **WHEN** người dùng chỉ cung cấp một khóa API duy nhất trong `GOOGLE_API_KEY`
- **THEN** hệ thống sử dụng khóa đó làm khóa chính cho mô hình chính và các mô hình dự phòng.

#### Scenario: Multiple API keys configured with key-first fallback
- **WHEN** người dùng cung cấp danh sách khóa `key_1, key_2` và danh sách model `model_A, model_B`
- **THEN** chuỗi fallback được sinh ra theo đúng thứ tự:
  1. `(model_A, key_1)` [Primary]
  2. `(model_A, key_2)` [Fallback 1: Giữ model_A, đổi sang key_2]
  3. `(model_B, key_1)` [Fallback 2: Chuyển sang model_B, dùng key_1]
  4. `(model_B, key_2)` [Fallback 3: Chuyển sang model_B, dùng key_2]

#### Scenario: Seamless key failover on HTTP 429
- **WHEN** lệnh gọi `(model_A, key_1)` ném lỗi `RateLimitError` (HTTP 429) do hết quota
- **THEN** LangChain tự động chuyển sang thực thi trên `(model_A, key_2)`
- **AND THEN** người dùng nhận được phản hồi thành công mà không nhận thông báo lỗi 503.

---

### Requirement: Multi-model fallback for Google chat models
Hệ thống SHALL cho phép cấu hình một mô hình chính (`GOOGLE_MODEL`, mặc định `gemini-3.1-flash-lite`) và danh sách các mô hình dự phòng (`GOOGLE_FALLBACK_MODELS`, mặc định `gemini-2.5-flash-lite,gemini-2.5-flash`) để tự động kích hoạt khi mô hình chính gặp lỗi quá tải hoặc bảo trì (HTTP 503/500).

#### Scenario: Automatic fallback to secondary Google model
- **WHEN** tất cả các API Key đều thất bại trên mô hình chính do mô hình bị quá tải (HTTP 503)
- **THEN** chuỗi fallback chuyển sang mô hình dự phòng tiếp theo trong danh sách `GOOGLE_FALLBACK_MODELS`.
- **AND THEN** câu trả lời vẫn tuân thủ đầy đủ định dạng trích dẫn pháp lý `<cite id="...">`.

---

### Requirement: Always-enabled Google query rewriter and summarizer
Hệ thống SHALL luôn kích hoạt tính năng Query Rewriting theo mặc định (`PIPELINE_REWRITER="llm"`) và thực thi cả Query Rewriter lẫn Conversational Memory Summarizer thông qua Google AI Studio thay vì hardcode model Ollama.

#### Scenario: Query rewriting execution via Google AI Studio
- **WHEN** người dùng gửi câu hỏi mới trong phiên hội thoại
- **THEN** Query Rewriter sử dụng mô hình Google Gemini để phân loại domain (`legal`/`chitchat`) và viết lại truy vấn độc lập.
- **AND THEN** không có lỗi kết nối nào phát sinh do thiếu Ollama daemon.

#### Scenario: Session memory summarization via Google AI Studio
- **WHEN** một lượt chat hoàn tất và tác vụ nền `summarize_session` được kích hoạt
- **THEN** bản tóm tắt được sinh ra thông qua Google Gemini và lưu vào PostgreSQL.

---

### Requirement: Minimal environment configuration and legacy pruning
Hệ thống SHALL loại bỏ toàn bộ các biến cấu hình không còn sử dụng (Ollama, FAISS, các tham số tuning chi tiết) ra khỏi file `.env` và `config.py`, chỉ giữ lại khoảng 20 biến cốt lõi cho pipeline.

#### Scenario: Starting backend with minimal .env
- **WHEN** backend khởi động với file `.env` tối giản chỉ chứa thông số Google API, Database và RAG cốt lõi
- **THEN** server khởi động thành công không cảnh báo thiếu biến môi trường.
- **AND THEN** các tham số nội bộ (batch size, retry count, dimension, device) tự động nạp giá trị mặc định tối ưu sẵn trong mã nguồn.

---

### Requirement: Frontend UI synchronization with Google AI Studio
Giao diện người dùng Next.js SHALL đồng bộ hóa danh sách mô hình và provider, chỉ hiển thị Google AI Studio cùng các mô hình Google Gemini được hỗ trợ (`gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, `gemini-2.5-flash`), loại bỏ toàn bộ các mô hình Ollama và HuggingFace cũ.

#### Scenario: User views model selector in chat UI
- **WHEN** người dùng mở giao diện chat
- **THEN** danh sách provider chỉ hiển thị "Google AI Studio".
- **AND THEN** danh sách mô hình chỉ gồm các biến thể Google Gemini với mặc định là `gemini-3.1-flash-lite`.
