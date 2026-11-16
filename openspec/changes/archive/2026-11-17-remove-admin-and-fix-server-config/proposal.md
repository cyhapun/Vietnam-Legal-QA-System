## Why

Hệ thống hiện tại đang cung cấp trang quản trị (`/admin`) cùng tab cấu hình AI (`SystemSettingsTab`) và cho phép client can thiệp trực tiếp vào các tham số hành vi của pipeline RAG (`candidateK`, `contextTokenBudget`, `cacheThreshold`, bật/tắt `enableReranker`, `enableQueryRewriter`, `enableSemanticCache`...). Việc cho phép phía giao diện ghi đè hành vi pipeline tiềm ẩn nguy cơ làm suy giảm nghiêm trọng độ chính xác của câu trả lời pháp luật (ví dụ: client vô tình tắt reranker hoặc cắt giảm ngân sách token context).

Đồng thời, cơ chế mang theo API key từ trình duyệt (BYOK) qua `inference_config` làm phức tạp hóa frontend với các modal cảnh báo và bộ nhớ cục bộ. Người dùng muốn chuyển toàn bộ hệ thống sang mô hình quản trị tinh gọn:
1. Xóa bỏ hoàn toàn trang admin và các cấu hình thừa thãi trên giao diện.
2. Khóa toàn bộ tham số hành vi của pipeline vào cấu hình server (`app/config.py` và `.env`).
3. Cố định việc sử dụng Google AI Studio với mô hình `gemini-3.1-flash-lite` và đọc API Key trực tiếp từ biến môi trường server (`GOOGLE_API_KEY`).

## What Changes

- **Xóa bỏ giao diện và API Admin:**
  - Xóa trang `frontend/app/admin/page.tsx` và API proxy `frontend/app/api/admin/[[...slug]]/route.ts`.
  - Xóa các component admin: `frontend/components/admin/SystemSettingsTab.tsx` và `frontend/components/admin/AnalyticsTab.tsx`.
  - Xóa router admin phía backend: `backend/app/api/admin.py` và bỏ đăng ký trong `backend/app/main.py`.
  - Cập nhật `frontend/components/chat/Sidebar.tsx`: gỡ bỏ liên kết "Quản trị", chỉ giữ lại "Kho Tài Liệu" (`/docs`) và "Đoạn chat mới".
- **Gỡ bỏ menu cấu hình tham số và modal BYOK trên Frontend:**
  - Xóa hoặc gỡ bỏ liên kết từ `frontend/components/chat/AdvancedSettings.tsx` (popover "Tham số") và `frontend/components/chat/InferenceSetupModal.tsx`.
  - Cố định lựa chọn mô hình tại `frontend/components/chat/ProviderSelector.tsx` sang Google Gemini Flash-Lite (`gemini-3.1-flash-lite`).
  - Dọn dẹp `frontend/components/chat/ChatInterface.tsx`: loại bỏ hoàn toàn việc đính kèm 15+ cờ tuning và credentials trong body của `POST /api/chat`.
- **Đơn giản hóa Schema Request và Controller phía Backend:**
  - Tinh giản `ChatRequest` trong `backend/app/models.py`: bỏ các trường runtime overrides (`candidateK`, `cacheThreshold`, `contextTokenBudget`, `enableReranker`, `enableQueryRewriter`, `enableSemanticCache`, `inference_config`...).
  - Cập nhật `backend/app/api/chat.py`: luôn sử dụng cấu hình chuẩn mực từ server (`app/config.py` và `.env`) cho số lượng ứng viên, reranking, semantic cache, và query rewriting.
  - Cố định backend sử dụng `GOOGLE_API_KEY` từ server environment cho tác vụ suy luận của Gemini Flash-Lite.

## Capabilities

### New Capabilities

- `server-authoritative-config`: Khóa toàn bộ tham số hành vi pipeline RAG và quản trị suy luận vào cấu hình máy chủ, ngăn chặn client can thiệp hoặc ghi đè sai lệch.

### Modified Capabilities

- `hybrid-inference-manager`: Chuyển hoàn toàn việc xác thực và cung cấp API key về server environment (`GOOGLE_API_KEY`), loại bỏ cơ chế nhận credentials từ request client.
- `user-configurable-inference-roles`: Cố định vai trò mô hình vào Google AI Studio (`gemini-3.1-flash-lite`), loại bỏ việc phân bổ vai trò runtime từ client.

## Impact

- **Frontend:** Giảm hơn 600 dòng code thừa, loại bỏ trang `/admin`, giảm tải dung lượng bundle, giao diện chat tập trung hoàn toàn vào trải nghiệm hỏi đáp.
- **Backend:** Schema `ChatRequest` sạch sẽ, rõ ràng; pipeline vận hành ổn định và đồng nhất theo đúng cấu hình chất lượng đã được tối ưu.
- **Bảo mật:** Không truyền nhận API keys qua HTTP payload giữa browser và server; toàn bộ API key được lưu giữ an toàn trong file `.env` trên máy chủ.
