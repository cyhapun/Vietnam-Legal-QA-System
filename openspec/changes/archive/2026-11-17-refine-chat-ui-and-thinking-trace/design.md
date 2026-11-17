# Design: Refine Chat UI, Thinking Trace and Brand Logo

## 1. Architectural Overview & Context

Mục tiêu của thiết kế là hiện đại hóa giao diện người dùng (UI) theo chuẩn của các trợ lý AI hàng đầu hiện nay (Gemini, ChatGPT), đồng bộ hóa logo/icon nhận diện thương hiệu mascot AI pháp luật, giải quyết triệt để lỗi CSS rendering modal xóa cuộc hội thoại, và loại bỏ các phần tử giao diện thừa gây rối mắt.

```
+---------------------------------------------------------------------------------------------------------+
|                                        Trình duyệt (Viewport)                                           |
|                                                                                                         |
| +-------------------+  +------------------------------------------------------------------------------+ |
| |  Sidebar (w-72)   |  |  ChatInterface                                                               | |
| |  [transform: ...] |  |                                                                              | |
| |  [🤖 VietLaw AI]  |  |  User: Hợp đồng chuyển nhượng quyền sử dụng đất có cần công chứng không?     | |
| |  Cuộc hội thoại 1 |  |                                                                              | |
| |  Cuộc hội thoại 2 |  |  Assistant (Avatar 🤖):                                                      | |
| |                   |  |  ┌─────────────────────────────────────────────────────────┐                | |
| |                   |  |  │ ✨ Đã tra cứu căn cứ pháp lý                          ▾ │ [Thinking Pill] | |
| |                   |  |  └─────────────────────────────────────────────────────────┘                | |
| |                   |  |                                                                              | |
| |                   |  |  Theo [Luật Đất đai 2024, Điều 27, Khoản 3]... (Link click -> CitationModal) | |
| |                   |  |  1. Trường hợp bắt buộc: Hợp đồng chuyển nhượng...                          | |
| |                   |  |                                                                              | |
| |                   |  |  [Sao chép] [Giải thích lại] | [👍] [👎]                                     | |
| +-------------------+  +------------------------------------------------------------------------------+ |
|                                                                                                         |
| +-----------------------------------------------------------------------------------------------------+ |
| | Modal Portal (document.body) - Luôn CĂN CHÍNH GIỮA 100% TOÀN BỘ MÀN HÌNH                            | |
| | ┌──────────────────────────────────────┐                                                            | |
| | │ 🗑️ Xóa hội thoại?                    │                                                            | |
| | │ Bạn có chắc chắn muốn xóa không?...  │                                                            | |
| | │                 [Hủy bỏ] [Xác nhận]  │                                                            | |
| | └──────────────────────────────────────┘                                                            | |
| +-----------------------------------------------------------------------------------------------------+ |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Chi Tiết Kỹ Thuật

### 2.1. Nhận Diện Thương Hiệu: Đồng Bộ Logo & Icon Mascot Mới

#### Asset chuẩn hóa:
- Cắt và chuẩn hóa hình ảnh mascot AI pháp luật (chú robot cầm cán cân công lý với cuộn văn bản luật) thành tỷ lệ vuông sắc nét (`571x571` px PNG).
- Lưu trữ tại:
  - `frontend/public/logo.png`
  - `frontend/app/icon.png` (favicon tự động của Next.js App Router)

#### Điểm tích hợp giao diện:
1. **Header Sidebar (`frontend/components/chat/Sidebar.tsx`)**:
   - Thay thế icon Lucide `Scale` trong khung gradient vuông bằng hình ảnh Logo mascot bo góc với viền sáng tinh tế và shadow nhẹ.
2. **Avatar phản hồi của Bot (`frontend/components/chat/ChatMessage.tsx`)**:
   - Thay thế icon Scale màu trắng trong hình tròn xanh bằng Avatar mascot robot (`rounded-full ring-1 ring-blue-500/20 shadow-sm`), giúp câu trả lời mang đậm tính nhận diện của trợ lý VietLaw AI.
3. **Màn hình chào mừng (`frontend/components/chat/ChatEmptyState.tsx`)**:
   - Thay thế khối vuông icon `Scale` bằng biểu tượng Logo mascot với kích thước lớn (`w-16 h-16 rounded-2xl shadow-xl shadow-blue-500/10`), tạo điểm nhấn ấn tượng ngay khi người dùng mở trang.
4. **Hiệu ứng chờ (`frontend/components/ui/LoadingSpinner.tsx`)**:
   - Sử dụng Logo mascot trong animation pulsing / loading của trợ lý ảo.

---

### 2.2. Căn giữa Modal Xóa Hội Thoại bằng React Portal

#### Vấn đề:
`Sidebar.tsx` nằm trong container `<div className="fixed inset-y-0 left-0 z-40 h-full w-72 ... transition-transform ...">` ở `ChatInterface.tsx`. Theo W3C CSS Transforms Module Level 1, bất kỳ giá trị transform nào khác `none` sẽ biến phần tử đó thành containing block cho `position: fixed`. Do đó, Modal đặt trong Sidebar bị gò bó trong phạm vi `w-72` (288px) và lệch hẳn sang mép trái màn hình.

#### Giải pháp:
- Sử dụng `createPortal` từ `react-dom` để đưa DOM của modal ra gắn trực tiếp vào `document.body`.
- Quản lý trạng thái client-side hydration (`isMounted`) để tương thích 100% với Next.js SSR mà không gây hydration mismatch.
- Cấu trúc:
  ```tsx
  {mounted && sessionToDelete && createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-2xl p-6 w-[90%] max-w-sm transform transition-all animate-in zoom-in-95 duration-200">
        {/* Nội dung modal */}
      </div>
    </div>,
    document.body
  )}
  ```

---

### 2.3. Tái Thiết Kế Tiến Trình (Thinking Trace) Kiểu Gemini & ChatGPT

#### Hiện trạng:
`ChatProcessingTrace.tsx` vẽ một khối to nền xanh `bg-blue-50/60 dark:bg-blue-500/10` với các chấm tròn lớn chiếm nhiều không gian.

#### Thiết kế mới:
1. **Khi đang trong quá trình xử lý (`analyzing` | `searching` | `selecting` | `generating`)**:
   - Hiển thị inline status với icon `Sparkles` có hiệu ứng xoay/nhấp nháy nhẹ hoặc spinner thanh mảnh.
   - Text trạng thái mượt mà theo từng giai đoạn:
     - `analyzing`: "Đang phân tích câu hỏi..."
     - `searching`: "Đang tìm kiếm căn cứ pháp lý..."
     - `selecting`: "Đang đối chiếu và chọn lọc quy định..."
     - `generating`: "Đang soạn thảo câu trả lời..."
   - Phong cách: Typography `text-xs font-medium text-slate-500 dark:text-slate-400`, không dùng nền màu hoặc viền hộp dày.
2. **Khi đã hoàn tất (`completed`)**:
   - Thu gọn thành một pill/accordion tinh tế:
     - Biểu tượng: `Sparkles` hoặc `Check` nhỏ + text `"Đã tra cứu căn cứ pháp lý"` + icon `ChevronDown` mờ.
     - Khi click vào: Mở rộng dropdown timeline với các bước đã thực hiện:
       - Đường line dọc siêu mỏng màu xám/xanh nhạt.
       - Mỗi bước có checkmark nhỏ màu ngọc bích (`text-emerald-500`) và text `text-xs text-slate-600 dark:text-slate-300`.
       - Nút đóng/thu gọn trực quan.
3. **Khi lỗi hoặc dừng (`error` | `cancelled`)**:
   - Hiển thị nhẹ nhàng với icon cảnh báo tinh gọn màu xám/đỏ nhạt, kèm nút "Thử lại".

---

### 2.4. Loại Bỏ Nút Căn Cứ Pháp Lý Dưới Chân và Side Drawer

#### Hiện trạng:
- `ChatMessage.tsx`: Render component `<LegalSourcesTrigger ... />` (`[📖 Căn cứ pháp lý 5 >]`).
- `ChatInterface.tsx`: Render `<div id="legal-sources-panel">` trượt từ mép phải màn hình chứa `<LegalSourceList sources={drawerContext} />`.

#### Thay đổi:
1. Xóa bỏ `<LegalSourcesTrigger />` khỏi `ChatMessage.tsx`.
2. Xóa bỏ state `drawerContext`, `setDrawerContext` và container Drawer bên phải trong `ChatInterface.tsx`.
3. Giữ nguyên:
   - Các thẻ `<cite id="...">` render dạng liên kết markdown màu xanh trong nội dung câu trả lời.
   - Cơ chế click vào thẻ `<cite>` mở `CitationModal` pop-up để tra cứu nhanh toàn văn điều luật.
   - Xóa bỏ hoặc tinh giản file `LegalSources.tsx` chỉ giữ lại hàm tiện ích nếu cần thiết.

---

### 2.5. Cập Nhật Script Kiểm Thử `verify-chat-ux.mjs`

- Điều chỉnh các assertions trong `frontend/scripts/verify-chat-ux.mjs`:
  - Loại bỏ các điều kiện kiểm tra bắt buộc sự xuất hiện của `LegalSourcesTrigger` và `id="legal-sources-panel"`.
  - Giữ lại hoặc bổ sung các assertion kiểm tra `CitationModal`, logo mascot mới, các nhãn tiến trình mới, và đảm bảo không có từ khóa kỹ thuật cấm (`retrieval score`, `reranker score`...).
