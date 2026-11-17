# Proposal: Remove Document Library Module

## 1. Problem Statement
Hệ thống VietLaw AI được định hình là trợ lý hỏi đáp pháp luật thông minh (AI Legal Assistant) chuyên sâu. Trước đây, hệ thống cung cấp một trang giao diện "Kho Tài Liệu" (`/docs`) cùng các component đính kèm (`DocumentList`, `ChunkViewer`, `UploadModal`) và một API proxy phía frontend (`/api/documents`) nhằm mục đích cho phép người dùng xem và upload văn bản trực tiếp từ trình duyệt.

Sau khi hệ thống chuyển đổi sang mô hình quản trị tinh gọn (`server-authoritative-config`), toàn bộ quy trình nạp dữ liệu pháp luật (ingestion) đã được chuẩn hóa qua các script dòng lệnh backend và cơ sở dữ liệu chuyên dụng (PostgreSQL + Qdrant), không còn phụ thuộc vào việc upload qua giao diện người dùng.

Sự tồn tại của nút "Kho Tài Liệu" trên thanh Sidebar và trang `/docs`:
- Làm phân tán trải nghiệm người dùng, khiến giao diện trở nên rườm rà trong khi mục đích chính của hệ thống là trợ lý hỏi đáp pháp lý.
- Tăng kích thước gói bundle frontend với các component viewer/upload không còn phục vụ người dùng cuối.
- Dễ gây nhầm lẫn về chức năng khi người dùng truy cập vào trang quản lý tài liệu.

Người dùng yêu cầu gỡ bỏ hoàn toàn module Kho Tài Liệu khỏi giao diện frontend để thanh điều hướng và ứng dụng trở nên tinh gọn tuyệt đối.

## 2. Proposed Changes
1. **Gỡ bỏ liên kết Kho Tài Liệu trên Sidebar:**
   - Cập nhật `frontend/components/chat/Sidebar.tsx`: Xóa bỏ thẻ `<Link href="/docs">...Kho Tài Liệu</Link>` và import icon `LibraryBig`.
   - Giữ lại duy nhất nút hành động `+ Đoạn chat mới` ở phần trên cùng của Sidebar, theo sau là thanh tìm kiếm và danh sách các đoạn chat.

2. **Xóa bỏ các trang và component của Kho Tài Liệu:**
   - Xóa bỏ trang `frontend/app/docs/page.tsx` và thư mục `frontend/app/docs/`.
   - Xóa bỏ toàn bộ thư mục `frontend/components/docs/` bao gồm:
     * `DocumentList.tsx`
     * `ChunkViewer.tsx`
     * `UploadModal.tsx`

3. **Xóa bỏ API proxy không còn dùng:**
   - Xóa bỏ route proxy `frontend/app/api/documents/[[...slug]]/route.ts` và thư mục `frontend/app/api/documents/`.

4. **Cấu hình chuyển hướng an toàn (Redirect Fallback):**
   - Trong `frontend/next.config.ts`, cấu hình redirect từ `/docs` về trang chủ `/` (permanent: false). Điều này bảo đảm nếu người dùng truy cập từ lịch sử duyệt web hoặc bookmark cũ, họ sẽ được điều hướng êm ái về trang chat chính thay vì gặp lỗi 404.

## 3. Goals & Non-Goals

### Goals
- Xóa bỏ 100% nút "Kho Tài Liệu" trên giao diện Sidebar.
- Dọn dẹp sạch sẽ toàn bộ mã nguồn thừa (`docs/` page, components, API proxy) ở frontend.
- Cấu hình chuyển hướng `/docs` về `/`.
- Bảo đảm TypeScript kiểm tra không lỗi (`tsc --noEmit`), build thành công (`npm run build`), và kiểm thử hồi quy đạt 100%.

### Non-Goals
- Không xóa các router backend `/api/documents` trong FastAPI (`backend/app/api/documents.py`), nhằm giữ khả năng phục vụ cho các script CLI quản trị hoặc kiểm tra dữ liệu nội bộ.
- Không can thiệp vào thanh "Căn cứ pháp lý" (Sources Panel) bên trong giao diện chat hỏi đáp.
