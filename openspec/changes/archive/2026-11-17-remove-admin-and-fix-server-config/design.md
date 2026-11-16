# Technical Design: Remove Admin Page & Lock Server-Authoritative Config

## 1. Bối cảnh & Mục tiêu thiết kế

Hệ thống RAG Pháp luật Việt Nam cần bảo đảm chất lượng trích dẫn và tính nhất quán cao nhất. Việc cho phép giao diện người dùng ghi đè các tham số của pipeline (như bỏ qua Reranker hoặc thu hẹp ngân sách token) không còn phù hợp với mục tiêu vận hành thực tế.

Mục tiêu thiết kế:
- **Xóa bỏ toàn bộ bề mặt Admin:** Loại bỏ trang `/admin`, router `/api/admin`, các tab phân tích/cài đặt và các nút dẫn đến admin.
- **Server-Authoritative Pipeline:** Backend chịu trách nhiệm 100% quyết định các tham số pipeline (kích thước ứng viên, reranking, semantic cache, query rewriting).
- **Cố định Provider & Model:** Cố định suy luận sang Google AI Studio với mô hình `gemini-3.1-flash-lite`, sử dụng biến môi trường server `GOOGLE_API_KEY`.

---

## 2. Kiến trúc luồng yêu cầu trước và sau thay đổi

### Trước thay đổi:
```text
Client (ChatInterface)
  ├─ Gửi câu hỏi + 18 cờ tuning (enableReranker, candidateK, contextTokenBudget...)
  ├─ Gửi BYOK API keys (Google key, HF key) từ browser storage
  └─ Menu Tham số trỏ về /admin#settings
       ▼
Backend (api/chat.py)
  ├─ Đọc ChatRequest với 18 trường override
  ├─ Ghi đè pipeline (bypass reranker nếu client gửi false)
  └─ Tạo dynamic LLM/embedding client theo credentials trong request
```

### Sau thay đổi:
```text
Client (ChatInterface)
  ├─ Chỉ gửi: { messages, sessionId, sessionTitle, messageId, category }
  └─ Model cố định: gemini-3.1-flash-lite (Google AI Studio)
       ▼
Backend (api/chat.py)
  ├─ Đọc ChatRequest tinh gọn
  ├─ Sử dụng 100% cấu hình chuẩn từ app/config.py và .env:
  │    ├─ RETRIEVER_CANDIDATE_K = 10
  │    ├─ RETRIEVER_K = 5
  │    ├─ PIPELINE_CONFIG["reranking"] = "cross_encoder"
  │    └─ CONTEXT_TOKEN_BUDGET = 6000
  └─ Khởi tạo LLM trực tiếp từ GOOGLE_API_KEY trong .env
```

---

## 3. Thiết kế chi tiết từng phần

### 3.1. Frontend Cleanup & Simplification

1. **Xóa các file và thư mục không còn dùng:**
   - `frontend/app/admin/page.tsx`
   - `frontend/app/api/admin/[[...slug]]/route.ts`
   - `frontend/components/admin/SystemSettingsTab.tsx`
   - `frontend/components/admin/AnalyticsTab.tsx`
   - `frontend/components/admin/` (xóa thư mục)
   - `frontend/components/chat/AdvancedSettings.tsx` (xóa popover Tham số)
   - `frontend/components/chat/InferenceSetupModal.tsx` (xóa modal cảnh báo BYOK)

2. **Cập nhật `frontend/components/chat/Sidebar.tsx`:**
   - Xóa khối `<Link href="/admin">` (nút "Quản trị").
   - Giữ nguyên nút "Đoạn chat mới" (`Plus`) và "Kho Tài Liệu" (`/docs`).

3. **Cập nhật `frontend/components/chat/ProviderSelector.tsx`:**
   - Cố định hiển thị mô hình `Google AI Studio: Gemini 3.1 Flash-Lite` (`gemini-3.1-flash-lite`).
   - Có thể vô hiệu hóa dropdown hoặc chỉ hiển thị badge model cố định vì không còn nhu cầu đổi sang provider khác không có API key.

4. **Cập nhật `frontend/components/chat/ChatInterface.tsx`:**
   - Gỡ bỏ import `AdvancedSettings`, `InferenceSetupModal`.
   - Thu gọn payload gửi tới `/api/chat`:
     ```typescript
     body: JSON.stringify({
       messages: apiMessages,
       model: 'gemini-3.1-flash-lite',
       sessionId: currentSessionId || 'unknown',
       sessionTitle: currentSessionTitle,
       messageId: userMessage.id,
       category: lawCategory,
     })
     ```
   - Xóa bỏ việc theo dõi và áp dụng `aiSettings` phức tạp.

5. **Đơn giản hóa `frontend/lib/ai-settings.ts` & `hooks/use-ai-settings.ts`:**
   - Rút gọn hoặc giữ lại chỉ các trạng thái tối giản cần thiết cho chat (nếu có), loại bỏ toàn bộ 15+ cờ tuning behavior và lưu trữ credentials.

### 3.2. Backend Simplification

1. **Gỡ bỏ router Admin:**
   - Xóa file `backend/app/api/admin.py`.
   - Trong `backend/app/main.py`: bỏ dòng import và đăng ký router `admin_router`.

2. **Tinh giản `ChatRequest` trong `backend/app/models.py`:**
   ```python
   class ChatRequest(BaseModel):
       model_config = ConfigDict(populate_by_name=True)

       messages: List[Message]
       model: Optional[str] = "gemini-3.1-flash-lite"
       sessionId: Optional[str] = "unknown"
       sessionTitle: Optional[str] = "Cuộc trò chuyện mới"
       messageId: Optional[str] = None
       category: str = "all"
   ```
   - Xóa bỏ các trường: `temperature`, `maxTokens`, `topK`, `candidateK`, `cacheThreshold`, `maxSubqueries`, `historyMessages`, `contextTokenBudget`, `maxCitations`, `llmTimeout`, `streaming`, `useHistoryForRewriter`, `enableQueryRewriter`, `enableReranker`, `enableSemanticCache`, `enableMemory`, `inference_config`.

3. **Cập nhật `backend/app/api/chat.py`:**
   - Các tham số pipeline được đọc trực tiếp từ `app.config`:
     - Số ứng viên rerank: `RETRIEVER_CANDIDATE_K`
     - Số tài liệu trả về: `RETRIEVER_K`
     - Bật/tắt reranker: kiểm tra `PIPELINE_CONFIG["reranking"] != "none"`
     - Bật/tắt semantic cache: `ENABLE_SEMANTIC_CACHE`
     - Ngưỡng semantic cache: `SEMANTIC_CACHE_THRESHOLD`
     - Token budget: hằng số server (mặc định 6000)
     - Model LLM: luôn sử dụng `GOOGLE_FALLBACK_MODEL` hoặc model từ server config với `GOOGLE_API_KEY`.
   - Không còn phụ thuộc vào `request.inference_config`.

---

## 4. Kế hoạch xác thực (Verification Plan)

1. **Kiểm tra Frontend:**
   - `npm run build` từ thư mục `frontend/` phải thành công không có lỗi type check hay missing routes.
   - Truy cập `http://localhost:3000`: giao diện chat tải sạch sẽ, không còn nút Quản trị, không còn popup Inference setup.
   - Truy cập `http://localhost:3000/admin`: trả về 404 Not Found.
2. **Kiểm tra Backend:**
   - Chạy test suites trong `backend/tests/` để bảo đảm các endpoint `/chat` và `/readiness` hoạt động chính xác.
   - Gửi request chat thử nghiệm: câu trả lời được sinh ra từ Google Gemini Flash-Lite có căn cứ pháp lý rõ ràng.
