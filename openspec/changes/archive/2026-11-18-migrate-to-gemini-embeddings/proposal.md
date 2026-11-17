# Proposal: Migrate Embedding Pipeline to Google Gemini Embeddings

## 1. Problem Statement
Hiện tại, VietLaw AI gặp phải trở ngại lớn khi chuẩn bị triển khai lên môi trường Cloud/Serverless (Vercel):
1. **Lỗi `402 Payment Required` từ Hugging Face Serverless API:** Cổng định tuyến mới `router.huggingface.co` của Hugging Face bắt buộc tài khoản phải có nạp sẵn pre-paid credits hoặc gói PRO để gọi API embedding, khiến chế độ `HUGGINGFACE_EMBEDDING_MODE=api` không thể hoạt động trên tài khoản miễn phí.
2. **Không thể chạy mô hình local trên Vercel:** Mô hình local fine-tuned `vietlaw-bge-m3-finetuned` có dung lượng file weights lên tới ~2.2 GB và tiêu tốn nhiều RAM, vượt quá ngưỡng giới hạn tài nguyên của môi trường Serverless Function trên Vercel (1 GB – 3 GB RAM, thời gian khởi động nhanh).
3. **Phân mảnh cấu hình:** Việc sử dụng Google AI Studio cho LLM Inference nhưng lại phụ thuộc vào Hugging Face cho Text Embedding làm phức tạp hóa khâu quản lý API key và tiềm ẩn rủi ro đứt gãy dịch vụ.

## 2. Proposed Changes
Chuyển đổi toàn diện tầng Text Embedding sang **Google Gemini Embedding API (`models/gemini-embedding-001`)**:
1. **Xây dựng `GeminiEmbedding` Adapter:** Tạo module nhúng vector sử dụng API chính thức của Google Gemini (`embedContent` và `batchEmbedContents`) hỗ trợ xuất vector chuẩn 1024 chiều (`outputDimensionality: 1024`), phân tách tác vụ `RETRIEVAL_DOCUMENT` cho văn bản luật và `RETRIEVAL_QUERY` cho câu hỏi người dùng.
2. **Kế thừa cơ chế xoay vòng Key (Multi-Key Rotation):** Sử dụng chung danh sách `GOOGLE_API_KEYS` đã có sẵn, tự động chuyển key khi gặp giới hạn hạn mức quota (429 Rate Limit).
3. **Tái nhúng (Re-index) và đồng bộ lên Qdrant Cloud:** Chạy script xử lý batching 5.758 điều khoản luật hiện có với vector 1024-dim của Gemini, cập nhật đè lên collection `vietlaw_clauses` trên Qdrant Cloud.
4. **Cập nhật cấu hình hệ thống:** Tinh chỉnh `backend/app/config.py`, `vercel.json`, `.env` và `.env.example` để kích hoạt Google Gemini Embedding làm mô hình nhúng mặc định cho cả môi trường Local và Serverless.

## 3. Goals & Non-Goals

### Goals
- Loại bỏ hoàn toàn sự phụ thuộc vào Hugging Face API key và khắc phục triệt để lỗi `402 Payment Required`.
- Cho phép cả Local và Vercel Serverless sử dụng chung một cơ chế nhúng Cloud API miễn phí 100%, không yêu cầu thẻ tín dụng.
- Duy trì số chiều vector 1024-dim tương thích với cấu trúc collection Qdrant Cloud hiện tại.
- Hoàn tất re-index toàn bộ 5.758 điều khoản trong vòng dưới 2 phút.
- Đảm bảo độ chính xác truy vấn RAG và trích dẫn điều khoản luật (citations) giữ nguyên chất lượng cao.

### Non-Goals
- Không thay đổi cấu trúc dữ liệu quan hệ trên Supabase PostgreSQL (bảng `laws`, `clauses`, `chat_sessions`, v.v.).
- Không thay đổi mô hình LLM chính (`gemini-3.1-flash-lite`) và luồng Streaming response.
