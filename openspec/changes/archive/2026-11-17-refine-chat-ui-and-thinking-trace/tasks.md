# Tasks: Refine Chat UI, Thinking Trace and Brand Logo

## 1. Chuẩn Hóa Asset & Tích Hợp Logo / Icon Thương Hiệu Mới
- [x] 1.1 Cắt hình ảnh mascot vuông sắc nét và cập nhật vào `frontend/public/logo.png` và `frontend/app/icon.png`.
- [x] 1.2 Cập nhật Header trong `frontend/components/chat/Sidebar.tsx` để hiển thị logo mascot mới.
- [x] 1.3 Cập nhật Avatar tin nhắn bot trong `frontend/components/chat/ChatMessage.tsx` sang hình ảnh mascot.
- [x] 1.4 Cập nhật màn hình chào mừng trong `frontend/components/chat/ChatEmptyState.tsx` với biểu tượng logo mascot lớn.
- [x] 1.5 Cập nhật biểu tượng trong `frontend/components/ui/LoadingSpinner.tsx`.

## 2. Căn giữa Modal Xác nhận Xóa Hội thoại (Sidebar.tsx)
- [x] 2.1 Thêm state `mounted` trong `frontend/components/chat/Sidebar.tsx` để hỗ trợ safe client-side hydration.
- [x] 2.2 Dùng `createPortal(modalJSX, document.body)` để đưa modal xác nhận xóa ra khỏi cây DOM của sidebar.
- [x] 2.3 Kiểm tra giao diện modal: lớp phủ `backdrop-blur-sm`, `z-[100]`, căn chính giữa 100% viewport trên cả mobile và desktop.

## 3. Tái Thiết Kế Tiến Trình Xử Lý theo Phong Cách Gemini / ChatGPT (ChatProcessingTrace.tsx)
- [x] 3.1 Thiết kế trạng thái active inline: icon Sparkles/Brain với hiệu ứng chuyển động nhẹ và text trạng thái tuần tự cho các giai đoạn (`analyzing`, `searching`, `selecting`, `generating`).
- [x] 3.2 Thiết kế trạng thái hoàn tất (`completed`): tự động thu gọn thành pill tinh tế (`✨ Đã tra cứu căn cứ pháp lý` + icon Chevron) thay vì khung hộp thô lớn.
- [x] 3.3 Thiết kế timeline chi tiết khi người dùng click mở rộng: danh sách các bước dạng timeline tối giản với checkmark xanh, typography thanh thoát.
- [x] 3.4 Tinh chỉnh trạng thái lỗi (`error`) và hủy (`cancelled`) nhẹ nhàng, tích hợp nút thử lại.

## 4. Loại Bỏ Nút Trigger Căn Cứ Pháp Lý & Side Drawer
- [x] 4.1 Xóa bỏ component `<LegalSourcesTrigger ... />` ở cuối tin nhắn bot trong `frontend/components/chat/ChatMessage.tsx`.
- [x] 4.2 Xóa bỏ state `drawerContext`, `setDrawerContext` và khối Side Drawer `#legal-sources-panel` trong `frontend/components/chat/ChatInterface.tsx`.
- [x] 4.3 Đảm bảo liên kết trích dẫn inline `<cite id="...">` và popup `CitationModal` tiếp tục hoạt động trơn tru.
- [x] 4.4 Dọn dẹp các import thừa và component không còn sử dụng trong `LegalSources.tsx`.

## 5. Kiểm Thử & Xác Minh Toàn Diện
- [x] 5.1 Cập nhật các assertions trong `frontend/scripts/verify-chat-ux.mjs` cho phù hợp với cấu trúc UX và logo mới.
- [x] 5.2 Chạy `npm run verify:chat-ux` trong `frontend/` để kiểm tra toàn bộ điều kiện UX.
- [x] 5.3 Kiểm tra build TypeScript (`npm run build` hoặc `npm run lint`) của frontend.
- [x] 5.4 Kiểm tra trực quan trên trình duyệt (thử nghiệm luồng hỏi đáp, logo hiển thị sắc nét, mở modal xóa và quan sát tiến trình mới).
