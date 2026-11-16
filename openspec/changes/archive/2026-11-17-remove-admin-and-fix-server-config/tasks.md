## 1. Frontend: Xóa bỏ Admin & Giao diện Cấu hình

- [x] 1.1 Xóa file trang admin `frontend/app/admin/page.tsx` và thư mục `frontend/app/admin`.
- [x] 1.2 Xóa proxy route admin `frontend/app/api/admin/[[...slug]]/route.ts` và thư mục `frontend/app/api/admin`.
- [x] 1.3 Xóa các components trong `frontend/components/admin/` (`SystemSettingsTab.tsx`, `AnalyticsTab.tsx`) và xóa thư mục `frontend/components/admin`.
- [x] 1.4 Cập nhật `frontend/components/chat/Sidebar.tsx`: gỡ bỏ thẻ `<Link href="/admin">` (nút "Quản trị").
- [x] 1.5 Xóa component `frontend/components/chat/AdvancedSettings.tsx` và gỡ bỏ menu "Tham số" khỏi thanh chat.
- [x] 1.6 Xóa component `frontend/components/chat/InferenceSetupModal.tsx` và gỡ bỏ việc gọi modal này trong `ChatInterface.tsx`.

## 2. Frontend: Cố định Model & Rút gọn Payload

- [x] 2.1 Cập nhật `frontend/components/chat/ProviderSelector.tsx` để cố định hiển thị mô hình Google Gemini Flash-Lite (`gemini-3.1-flash-lite`).
- [x] 2.2 Tinh giản `frontend/components/chat/ChatInterface.tsx`: loại bỏ toàn bộ 15+ cờ tuning (`enableReranker`, `candidateK`, `contextTokenBudget`...) khỏi request body của `POST /api/chat`.
- [x] 2.3 Thu gọn hoặc dọn dẹp `frontend/lib/ai-settings.ts` và `frontend/hooks/use-ai-settings.ts` để không còn lưu trữ các cờ pipeline tuning và credentials thừa.
- [x] 2.4 Cập nhật script verify frontend `frontend/scripts/verify-inference-settings.mjs` (hoặc loại bỏ khỏi package.json) để tương thích với cấu trúc mới.

## 3. Backend: Xóa Router Admin & Tinh giản Schema

- [x] 3.1 Xóa file `backend/app/api/admin.py`.
- [x] 3.2 Cập nhật `backend/app/main.py`: gỡ bỏ import và đăng ký router `admin_router`.
- [x] 3.3 Tinh giản `ChatRequest` trong `backend/app/models.py`: chỉ giữ lại `messages`, `sessionId`, `sessionTitle`, `messageId`, `category`, và `model` (mặc định `gemini-3.1-flash-lite`).
- [x] 3.4 Cập nhật `backend/app/api/chat.py`: loại bỏ việc đọc các cờ override từ request; đọc toàn bộ tham số tìm kiếm, reranking, token budget, cache từ `app/config.py`.
- [x] 3.5 Cập nhật backend LLM service: cố định việc khởi tạo mô hình Google Gemini Flash-Lite sử dụng `GOOGLE_API_KEY` từ server environment.

## 4. Kiểm thử & Xác thực toàn diện

- [x] 4.1 Chạy unit tests phía backend (`pytest backend/tests`) để xác nhận tính toàn vẹn của API `/chat` và `/readiness`.
- [x] 4.2 Chạy build frontend (`npm run build`) từ thư mục `frontend/` và xác nhận không có lỗi type check hay gãy đường dẫn.
- [x] 4.3 Khởi động lại dịch vụ backend và frontend, xác minh trực tiếp:
  - Truy cập `http://localhost:3000/admin` trả về 404.
  - Giao diện chat hoạt động trơn tru không có popup hay menu tham số.
  - Đặt câu hỏi thử nghiệm và kiểm tra câu trả lời được sinh ra hoàn chỉnh với citation từ Gemini Flash-Lite.
