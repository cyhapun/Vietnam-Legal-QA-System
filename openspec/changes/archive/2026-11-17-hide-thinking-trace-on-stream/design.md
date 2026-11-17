# Design: Hide Thinking Trace on Answer Streaming

## 1. Architectural & UX Goals
Thiết kế này đảm bảo trải nghiệm hiển thị tiến trình tư duy (thinking trace) diễn ra liền mạch, tự nhiên và đúng thời điểm:
1. **Pre-response Visibility (Chỉ hiển thị khi chờ)**: Chỉ hiển thị thinking text trong giai đoạn hệ thống đang chuẩn bị (phân tích, tra cứu, chọn lọc điều luật), khi chưa có bất kỳ token nào của câu trả lời.
2. **Instant Dismissal on First Token (Ẩn lập tức khi có chữ)**: Ngay khi token đầu tiên được stream từ backend tới client, dòng tiến trình lập tức unmount, tập trung trọn vẹn sự chú ý của người dùng vào văn bản đang gõ.

---

## 2. Giao diện & Vòng Đời Tin Nhắn (Lifecycle Flow)

```
[BƯỚC 1: KHỞI TẠO & TRA CỨU - Content: ""]
UI:
  AI:
    ✦ Đang tra cứu căn cứ pháp lý...   <-- Hiển thị vì !content.trim()

[BƯỚC 2: BẮT ĐẦU STREAMING - Content: "Căn cứ theo Điều 45..."]
UI:
  AI:
    Căn cứ theo Điều 45 Luật Đất đai 2024... ▋
    <-- Dòng tiến trình ĐÃ ẨN vì content.trim() != ""

[BƯỚC 3: KẾT THÚC STREAM - Content: "Căn cứ theo Điều 45...", Stage: 'completed']
UI:
  AI:
    Căn cứ theo Điều 45 Luật Đất đai 2024, người sử dụng...
    
    10:45 AM   [📋]  [🔄]  │  [👍]  [👎]
```

---

## 3. Chi Tiết Thay Đổi Mã Nguồn

### 3.1 `frontend/components/chat/ChatMessage.tsx`

Cập nhật điều kiện render `ChatProcessingTrace`:

```tsx
// Trước:
{!isUser && message.processingStage && message.processingStage !== 'completed' && (
  <ChatProcessingTrace stage={message.processingStage} />
)}

// Sau:
{!isUser && !message.content?.trim() && message.processingStage && message.processingStage !== 'completed' && (
  <ChatProcessingTrace stage={message.processingStage} />
)}
```

### 3.2 `frontend/scripts/verify-chat-ux.mjs`

Thêm assertion xác thực:
```js
if (!chatMessage.includes('!message.content?.trim()')) {
  throw new Error('ChatMessage must only render processing trace when there is no streaming content yet (!message.content?.trim())');
}
```
