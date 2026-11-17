# Design: Remove Document Library Module

## 1. Overview & Architecture Changes

Mục tiêu thiết kế của thay đổi này là tinh giản triệt để bề mặt người dùng của VietLaw AI, biến ứng dụng thành một trợ lý đàm thoại thuần túy (Conversational AI Interface) tương tự phong cách ChatGPT/Claude, nơi thanh điều hướng bên trái chỉ tập trung vào việc quản lý hội thoại và tạo phiên chat mới.

```
          HIỆN TẠI (BEFORE)                              SAU KHI THAY ĐỔI (AFTER)
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│ [Logo] VietLaw AI               │           │ [Logo] VietLaw AI               │
│ ─────────────────────────────── │           │ ─────────────────────────────── │
│  [ + ] Đoạn chat mới            │           │  [ + ] Đoạn chat mới            │
│  [ 📚] Kho Tài Liệu (-> /docs)  │ ── XÓA ─▶ │                                 │
│ ─────────────────────────────── │           │ ─────────────────────────────── │
│  [ 🔍 ] Tìm kiếm đoạn chat...   │           │  [ 🔍 ] Tìm kiếm đoạn chat...   │
│                                 │           │                                 │
│  Danh sách hội thoại:           │           │  Danh sách hội thoại:           │
│   • Hôm nay                     │           │   • Hôm nay                     │
│   • Hôm qua                     │           │   • Hôm qua                     │
│   • 7 ngày trước                │           │   • 7 ngày trước                │
│                                 │           │                                 │
│  [⚙️] Chuyển theme Sáng/Tối     │           │  [⚙️] Chuyển theme Sáng/Tối     │
└─────────────────────────────────┘           └─────────────────────────────────┘
```

---

## 2. File Removal & Modification Details

### 2.1 Cập nhật `frontend/components/chat/Sidebar.tsx`
- **Xóa import:** Bỏ `LibraryBig` khỏi import `{ Plus, Search, MessageSquare, Trash2, LibraryBig, Sun, Moon, PanelLeftClose } from 'lucide-react'`.
- **Xóa nút điều hướng:**
  ```tsx
  // XÓA ĐOẠN MÃ NÀY:
  <Link
    href="/docs"
    className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-gray-200 dark:border-white/5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5 active:scale-98"
  >
    <LibraryBig className="w-4 h-4" />
    <span className="text-[13px] font-semibold">Kho Tài Liệu</span>
  </Link>
  ```
- **Kiểm tra import `Link`:** Nếu `Link` từ `'next/link'` không còn được sử dụng ở bất kỳ đâu trong `Sidebar.tsx`, gỡ bỏ cả `import Link from 'next/link'`.

### 2.2 Xóa bỏ các trang và component không dùng
- Xóa file `frontend/app/docs/page.tsx` và thư mục `frontend/app/docs`.
- Xóa các component:
  * `frontend/components/docs/ChunkViewer.tsx`
  * `frontend/components/docs/DocumentList.tsx`
  * `frontend/components/docs/UploadModal.tsx`
  * Xóa thư mục `frontend/components/docs`.
- Xóa API proxy:
  * `frontend/app/api/documents/[[...slug]]/route.ts`
  * Xóa thư mục `frontend/app/api/documents`.

### 2.3 Cập nhật `frontend/next.config.ts` (Redirects)
Bổ sung hàm `redirects` vào Next.js config:
```typescript
import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  output: 'standalone',
  transpilePackages: ['motion'],
  async redirects() {
    return [
      {
        source: '/docs',
        destination: '/',
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
```

---

## 3. Verification & Safety Analysis

1. **Dependency Check:**
   - Đã kiểm tra `git grep "components/docs"`: Chỉ có duy nhất `frontend/app/docs/page.tsx` import các component này.
   - Không có component nào trong `components/chat/` phụ thuộc vào `components/docs/` hoặc `/api/documents/`.
   - Các chức năng trích dẫn căn cứ pháp lý trong chat (`ChatMessage.tsx`, `ChatInterface.tsx`, `SourcesPanel.tsx`) sử dụng `DocumentChunk` từ `lib/types.ts` và SSE stream từ `/api/chat`, hoàn toàn không liên quan đến module docs.

2. **Redirect Validation:**
   - Khi truy cập `http://localhost:3000/docs`, server trả về mã `307 Temporary Redirect` chuyển hướng tức thì về `/`.
