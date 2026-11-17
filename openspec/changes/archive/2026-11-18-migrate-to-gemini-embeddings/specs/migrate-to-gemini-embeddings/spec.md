# migrate-to-gemini-embeddings Specification

## Purpose
Đặc tả kỹ thuật cho việc chuyển đổi toàn bộ pipeline tạo vector nhúng (text embedding) sang Google Gemini Embedding API (`gemini-embedding-001`), hỗ trợ xuất vector 1024 chiều và tái đồng bộ kho dữ liệu trên Qdrant Cloud.

## Requirements

### Requirement: Google Gemini Embedding Adapter Implementation
Hệ thống backend SHALL cung cấp adapter `GeminiEmbedding` kế thừa `BaseEmbedding` để tạo vector nhúng thông qua Google AI Studio API.

#### Scenario: Nhúng câu hỏi truy vấn (Single Query)
- **WHEN** hệ thống nhận câu hỏi truy vấn từ người dùng
- **THEN** adapter gọi API Google `embedContent` với `taskType: RETRIEVAL_QUERY` và `outputDimensionality: 1024`
- **AND THEN** trả về mảng số thực float có độ dài chính xác 1024 chiều.

#### Scenario: Nhúng lô văn bản (Batch Documents)
- **WHEN** hệ thống thực hiện nhúng danh sách điều khoản luật
- **THEN** adapter gọi API Google `batchEmbedContents` với `taskType: RETRIEVAL_DOCUMENT` và `outputDimensionality: 1024` theo từng lô không quá 100 văn bản
- **AND THEN** trả về danh sách các vector 1024 chiều tương ứng với từng văn bản đầu vào.

### Requirement: Multi-Key Quota Failover
Adapter `GeminiEmbedding` SHALL tự động xoay vòng qua danh sách `GOOGLE_API_KEYS` khi gặp lỗi hạn mức (HTTP 429 hoặc quota exceeded).

#### Scenario: Key chính bị hết hạn mức
- **WHEN** API key hiện tại trả về mã lỗi 429 hoặc thông báo hết quota
- **THEN** adapter tự động chuyển sang API key kế tiếp trong danh sách `GOOGLE_API_KEYS` mà không làm đứt đoạn tiến trình.

### Requirement: Cloud Vector Synchronization
Hệ thống SHALL cung cấp script để nhúng lại toàn bộ 5.758 điều khoản bằng Gemini Embedding và cập nhật đồng bộ lên Qdrant Cloud collection `vietlaw_clauses`.

#### Scenario: Tái lập chỉ mục Qdrant Cloud
- **WHEN** script `reindex_gemini_cloud.py` thực thi
- **THEN** toàn bộ 5.758 điều khoản từ Supabase được nhúng thành vector 1024 chiều mới của Gemini
- **AND THEN** collection `vietlaw_clauses` trên Qdrant Cloud có đủ 5.758 điểm vector với trạng thái `green` và đầy đủ payload index.
