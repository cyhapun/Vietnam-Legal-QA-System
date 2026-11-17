# Design: Shimmering Thinking Text & Trace Cleanup

## 1. Architectural & Visual Goals

Thiết kế này tái cấu trúc toàn diện thành phần hiển thị tiến trình của VietLaw AI:
1. **Loại bỏ cấu trúc hộp/bảng (Unboxed & Tableless)**: Chuyển đổi từ pill button đóng khung và danh sách timeline sang hiển thị dạng dòng text thuần túy thanh thoát.
2. **Hiệu ứng Shimmering Thinking Text**: Tận dụng CSS Keyframe animation với gradient lướt ngang qua văn bản, mang lại cảm nhận trực quan sống động giống các mô hình AI reasoning (Gemini, ChatGPT, DeepSeek).
3. **Cơ chế Xóa hoàn toàn khi Hoàn tất (Complete Cleanup on Complete)**: Ngay khi câu trả lời hoàn thiện (`processingStage === 'completed'`), component trả về `null` hoàn toàn, giúp khung tin nhắn sạch sẽ và tập trung tối đa vào nội dung câu trả lời.

---

## 2. Giao diện & Hiệu ứng Thị giác (UI Component Design)

### 2.1 Hiệu ứng CSS Shimmering (`globals.css`)

```css
@keyframes thinking-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.animate-thinking-shimmer {
  background: linear-gradient(90deg, #94a3b8 0%, #2563eb 50%, #94a3b8 100%);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: thinking-shimmer 2.5s infinite linear;
}

.dark .animate-thinking-shimmer {
  background: linear-gradient(90deg, #64748b 0%, #60a5fa 50%, #64748b 100%);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: thinking-shimmer 2.5s infinite linear;
}
```

### 2.2 Trạng thái Hiển thị của `ChatProcessingTrace.tsx`

```
[KHI ĐANG XỬ LÝ - ACTIVE]
✦ Đang tra cứu căn cứ pháp lý...   <-- Ánh sáng gradient chuyển động lướt qua chữ

[KHI HOÀN THÀNH - COMPLETED]
(Hoàn toàn biến mất khỏi DOM - Render null)
```

* **Icon**: Sử dụng icon nhỏ `<Sparkles className="w-3.5 h-3.5 animate-pulse text-blue-500 shrink-0" />`.
* **Nội dung hiển thị theo Stage**:
  - `analyzing`: *"Đang phân tích câu hỏi..."*
  - `searching`: *"Đang tra cứu căn cứ pháp lý..."*
  - `selecting`: *"Đang chọn lọc điều luật phù hợp..."*
  - `generating`: *"Đang tổng hợp câu trả lời..."*
* **Trạng thái kết thúc**:
  - `completed` hoặc `idle`: Trả về `null` (xóa hoàn toàn khỏi DOM).
  - `cancelled`: Dòng text xám nhẹ *"Đã dừng yêu cầu."*
  - `error`: Dòng text đỏ nhạt *"Không thể hoàn tất yêu cầu."*

---

### 2.3 Tinh chỉnh trong `ChatMessage.tsx`

- Loại bỏ state không còn dùng: `const [isProcessCollapsed, setIsProcessCollapsed] = useState(true);`.
- Render trực tiếp:
```tsx
{!isUser && message.processingStage && message.processingStage !== 'completed' && (
  <ChatProcessingTrace stage={message.processingStage} />
)}
```

---

## 3. Bảng Đối Chiếu Thay Đổi Mã Nguồn

| File | Thành phần | Thay đổi cụ thể |
| :--- | :--- | :--- |
| `frontend/app/globals.css` | Animation | Bổ sung keyframe `@keyframes thinking-shimmer` và class `.animate-thinking-shimmer` cho cả Light và Dark mode. |
| `frontend/components/chat/ChatProcessingTrace.tsx` | UI Component | Xóa toàn bộ viền, bảng, toggle; trả về `null` khi `completed`; render dòng text shimmering khi active. |
| `frontend/components/chat/ChatMessage.tsx` | Container | Xóa bỏ state collapse không cần thiết, chỉ hiển thị trace khi chưa completed. |
| `frontend/scripts/verify-chat-ux.mjs` | Test Suite | Cập nhật kiểm tra thinking text và xác nhận không còn tồn tại pill/table thừa sau khi hoàn tất. |
