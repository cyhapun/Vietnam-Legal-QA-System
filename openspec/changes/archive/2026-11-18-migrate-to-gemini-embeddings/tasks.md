# Tasks: Migrate Embedding Pipeline to Google Gemini Embeddings

## 1. Phát Triển Adapter Google Gemini Embedding
- [x] 1.1 Tạo module `backend/app/services/embedding/gemini.py` hiện thực hóa class `GeminiEmbedding` kế thừa `BaseEmbedding`.
- [x] 1.2 Cài đặt phương thức `embed_query` với `outputDimensionality: 1024` và `taskType: RETRIEVAL_QUERY`.
- [x] 1.3 Cài đặt phương thức `embed_documents` hỗ trợ chia batch tối đa 100 items và `taskType: RETRIEVAL_DOCUMENT`.
- [x] 1.4 Tích hợp logic xoay vòng `GOOGLE_API_KEYS` khi gặp lỗi hạn mức 429.

## 2. Tích Hợp Cấu Hình Hệ Thống
- [x] 2.1 Cập nhật `backend/app/services/embedding/__init__.py` để export `GeminiEmbedding`.
- [x] 2.2 Cập nhật `backend/app/config.py` hỗ trợ `EMBEDDING_PROVIDER="gemini"` cho cả hai runtime profile `local` và `serverless`.
- [x] 2.3 Cập nhật factory khởi tạo embedding trong `backend/app/services/provider_registry.py` hoặc các service liên quan để nạp `GeminiEmbedding`.

## 3. Tái Nhúng Kho Dữ Liệu Lên Qdrant Cloud
- [ ] 3.1 Xây dựng script `backend/scripts/reindex_gemini_cloud.py` đọc 5.758 điều khoản từ Supabase và gửi batch embed lên Gemini API.
- [ ] 3.2 Thực thi script, ghi đè vector 1024-dim mới vào collection `vietlaw_clauses` trên Qdrant Cloud.
- [ ] 3.3 Kiểm tra lại số lượng điểm (5.758 points) và tính hợp lệ của Payload Index trên Qdrant Cloud.

## 4. Tối Ưu Hóa Cấu Hình Môi Trường & Vercel
- [ ] 4.1 Cập nhật `vercel.json` để sử dụng Google Gemini embedding thay cho Hugging Face.
- [ ] 4.2 Cập nhật `.env` và `.env.example`: lược bỏ các biến Hugging Face không còn dùng, tinh chỉnh comment hướng dẫn cho Google Gemini.

## 5. Kiểm Thử & Nghiệm Thu Hệ Thống
- [ ] 5.1 Kiểm tra endpoint `/readiness`: xác nhận status `ready`, kết nối Supabase và Qdrant Cloud đều `ok`.
- [ ] 5.2 Kiểm thử truy vấn RAG chat (`/chat` và `/chat/stream`): xác nhận tìm kiếm chính xác điều khoản và stream câu trả lời hoàn hảo.
- [ ] 5.3 Chạy bộ kiểm thử tự động của dự án: `npm run verify:chat-ux` và pytest nếu có.
