# Design: Remove Generating Trace on Stream

## 1. Architectural & UX Goals
Thiết kế này loại bỏ hoàn toàn sự tồn tại của tiến trình hiển thị khi bước vào giai đoạn sinh câu trả lời (`generating`):
1. **Zero Distraction during Stream**: Khi token bắt đầu tuôn ra, không có bất kỳ dòng chữ tiến trình nào chạy song song bên dưới câu trả lời.
2. **Pre-Response Only**: Thu hẹp phạm vi của `ChatProcessingTrace` chỉ dành riêng cho 3 khâu chờ tìm kiếm: `analyzing`, `searching`, `selecting`.

---

## 2. Luồng Xử Lý & Điều Kiện Render (Dual Guard Architecture)

```
                       ┌────────────────────────────────┐
                       │ Người dùng gửi câu hỏi mới     │
                       └───────────────┬────────────────┘
                                       │
                                       ▼
                     [Giai đoạn Chờ - Pre-response]
            Stage: analyzing / searching / selecting (content: "")
                                       │
                                       ▼
                    Hiển thị Thinking Text Shimmering:
                     ✦ Đang phân tích câu hỏi...
                     ✦ Đang tra cứu căn cứ pháp lý...
                     ✦ Đang chọn lọc thông tin phù hợp...
                                       │
                                       ▼
                  [Token đầu tiên về từ SSE: event 'token']
                                       │
                      ┌────────────────┴───────────────┐
                      │                                │
                      ▼                                ▼
            processingStage = 'generating'    streamingText = 'Căn cứ...'
                      │                                │
                      └────────────────┬───────────────┘
                                       │
                                       ▼
                 [KÍCH HOẠT CHẶN KÉP - DUAL GUARD]
           1. ChatProcessingTrace: stage === 'generating' => return null!
           2. ChatMessage: !['completed', 'generating', 'idle'].includes(stage) => false!
                                       │
                                       ▼
                  TIẾN TRÌNH BIẾN MẤT HOÀN TOÀN (NULL)
             Chỉ còn câu trả lời đang gõ: "Căn cứ theo Điều 45... ▋"
```

---

## 3. Chi Tiết Thay Đổi Mã Nguồn

### 3.1 `frontend/components/chat/ChatProcessingTrace.tsx`

```tsx
function getThinkingText(stage: ChatProcessingStage): string {
  if (stage === 'analyzing') return 'Đang phân tích câu hỏi...';
  if (stage === 'searching') return 'Đang tra cứu căn cứ pháp lý...';
  if (stage === 'selecting') return 'Đang chọn lọc thông tin phù hợp...';
  return 'Đang suy nghĩ...';
}

export function ChatProcessingTrace({ stage }: ChatProcessingTraceProps) {
  // Hoàn toàn không hiển thị khi đã hoàn thành, idle hoặc khi đang generating (stream câu trả lời)
  if (stage === 'idle' || stage === 'completed' || stage === 'generating') return null;

  if (stage === 'cancelled') {
    return (
      <div className="my-1.5 flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 font-medium">
        <XCircle className="h-3.5 w-3.5 text-gray-400 dark:text-gray-500" />
        <span>Đã dừng yêu cầu</span>
      </div>
    );
  }

  if (stage === 'error') {
    return (
      <div className="my-1.5 flex items-center gap-1.5 text-xs text-rose-500 dark:text-rose-400 font-medium">
        <XCircle className="h-3.5 w-3.5 text-rose-500" />
        <span>Không thể hoàn tất yêu cầu</span>
      </div>
    );
  }

  return (
    <div className="my-1.5 flex items-center gap-2 py-0.5 text-[13px] font-medium" aria-live="polite">
      <Sparkles className="h-3.5 w-3.5 text-blue-500 dark:text-blue-400 animate-pulse shrink-0" />
      <span className="animate-thinking-shimmer">{getThinkingText(stage)}</span>
    </div>
  );
}
```

### 3.2 `frontend/components/chat/ChatMessage.tsx`

```tsx
{!isUser && !message.content?.trim() && message.processingStage && !['completed', 'generating', 'idle'].includes(message.processingStage) && (
  <ChatProcessingTrace stage={message.processingStage} />
)}
```

### 3.3 `frontend/scripts/verify-chat-ux.mjs`

- Cập nhật danh sách các nhãn kiểm tra: chỉ giữ lại 3 nhãn của các bước chờ.
- Kiểm tra `ChatProcessingTrace.tsx` chứa `stage === 'generating'` trong điều kiện trả về `null`.
- Xác nhận không còn nhãn `"Đang tổng hợp"` trong mã nguồn component.
