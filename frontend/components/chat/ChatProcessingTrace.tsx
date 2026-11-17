'use client';

import { Sparkles, XCircle } from 'lucide-react';

export type ChatProcessingStage =
  | 'idle'
  | 'analyzing'
  | 'searching'
  | 'selecting'
  | 'generating'
  | 'completed'
  | 'cancelled'
  | 'error';

interface ChatProcessingTraceProps {
  stage: ChatProcessingStage;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}

function getThinkingText(stage: ChatProcessingStage): string {
  if (stage === 'analyzing') return 'Đang phân tích câu hỏi...';
  if (stage === 'searching') return 'Đang tra cứu căn cứ pháp lý...';
  if (stage === 'selecting') return 'Đang chọn lọc thông tin phù hợp...';
  if (stage === 'generating') return 'Đang tổng hợp câu trả lời...';
  return 'Đang suy nghĩ...';
}

export function ChatProcessingTrace({ stage }: ChatProcessingTraceProps) {
  // Hoàn toàn không hiển thị khi đã hoàn thành hoặc idle
  if (stage === 'idle' || stage === 'completed') return null;

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

  // Active thinking text with sparkling icon and shimmer wave effect
  return (
    <div className="my-1.5 flex items-center gap-2 py-0.5 text-[13px] font-medium" aria-live="polite">
      <Sparkles className="h-3.5 w-3.5 text-blue-500 dark:text-blue-400 animate-pulse shrink-0" />
      <span className="animate-thinking-shimmer">{getThinkingText(stage)}</span>
    </div>
  );
}
