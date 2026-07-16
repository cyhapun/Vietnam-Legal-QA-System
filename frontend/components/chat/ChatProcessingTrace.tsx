'use client';

import { Check, ChevronDown, Circle, Loader2, Square, XCircle } from 'lucide-react';

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
  onCancel?: () => void;
}

const STEPS: Array<{ key: ChatProcessingStage; label: string }> = [
  { key: 'analyzing', label: 'Đang phân tích câu hỏi' },
  { key: 'searching', label: 'Đang tra cứu căn cứ pháp lý' },
  { key: 'selecting', label: 'Đang chọn lọc thông tin phù hợp' },
  { key: 'generating', label: 'Đang tổng hợp câu trả lời' },
];

const ORDER: Record<ChatProcessingStage, number> = {
  idle: -1,
  analyzing: 0,
  searching: 1,
  selecting: 2,
  generating: 3,
  completed: 4,
  cancelled: -1,
  error: -1,
};

function getTitle(stage: ChatProcessingStage): string {
  if (stage === 'completed') return 'Tra cứu hoàn tất';
  if (stage === 'cancelled') return 'Đã dừng yêu cầu';
  if (stage === 'error') return 'Không thể hoàn tất câu trả lời';
  if (stage === 'generating') return 'Đang chuẩn bị câu trả lời';
  return 'Đang tra cứu pháp luật';
}

function getDescription(stage: ChatProcessingStage): string {
  if (stage === 'completed') return 'Bạn có thể xem lại các bước xử lý khi cần.';
  if (stage === 'cancelled') return 'Yêu cầu đã được dừng. Bạn có thể chỉnh sửa câu hỏi hoặc gửi câu hỏi mới.';
  if (stage === 'error') return 'Vui lòng thử lại hoặc mô tả câu hỏi cụ thể hơn.';
  return 'Quá trình này có thể mất thêm một chút thời gian.';
}

export function ChatProcessingTrace({
  stage,
  collapsed = false,
  onToggleCollapsed,
  onCancel,
}: ChatProcessingTraceProps) {
  if (stage === 'idle') return null;

  const activeIndex = ORDER[stage];
  const isDone = stage === 'completed';
  const isTerminal = isDone || stage === 'cancelled' || stage === 'error';

  if (collapsed && isTerminal) {
    return (
      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2 text-sm text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="flex w-full items-center justify-between gap-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 rounded-lg"
          aria-expanded="false"
        >
          <span className="inline-flex items-center gap-2 font-medium">
            {isDone ? <Check className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-slate-500" />}
            {getTitle(stage)}
          </span>
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 dark:text-blue-300">
            Xem quá trình
            <ChevronDown className="h-3.5 w-3.5" />
          </span>
        </button>
      </div>
    );
  }

  return (
    <section
      className="mt-3 rounded-2xl border border-blue-100 bg-blue-50/60 p-4 shadow-sm dark:border-blue-500/20 dark:bg-blue-500/10"
      aria-live={isTerminal ? 'polite' : 'polite'}
      aria-label="Tiến trình xử lý"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            {isDone ? (
              <Check className="h-4 w-4 text-emerald-600" />
            ) : stage === 'cancelled' || stage === 'error' ? (
              <XCircle className="h-4 w-4 text-slate-500" />
            ) : (
              <Loader2 className="h-4 w-4 animate-spin text-blue-600 motion-reduce:animate-none" />
            )}
            {getTitle(stage)}
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
            {getDescription(stage)}
          </p>
        </div>

        {isTerminal && onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="shrink-0 rounded-lg px-2 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:text-blue-300 dark:hover:bg-blue-500/20"
            aria-expanded="true"
          >
            Ẩn quá trình
          </button>
        )}
      </div>

      <ol className="mt-3 space-y-2">
        {STEPS.map((step, index) => {
          const complete = isDone || activeIndex > index;
          const active = !isTerminal && activeIndex === index;
          return (
            <li key={step.key} className="flex items-center gap-2 text-sm">
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                  complete
                    ? 'border-emerald-500 bg-emerald-500 text-white'
                    : active
                      ? 'border-blue-500 bg-white text-blue-600 dark:bg-slate-950'
                      : 'border-slate-300 bg-white text-slate-400 dark:border-slate-700 dark:bg-slate-950'
                }`}
              >
                {complete ? <Check className="h-3 w-3" /> : active ? <Loader2 className="h-3 w-3 animate-spin motion-reduce:animate-none" /> : <Circle className="h-2 w-2 fill-current" />}
              </span>
              <span className={`${complete ? 'text-slate-700 dark:text-slate-200' : active ? 'font-semibold text-blue-800 dark:text-blue-200' : 'text-slate-500 dark:text-slate-400'}`}>
                {complete ? step.label.replace('Đang ', 'Đã ') : step.label}
              </span>
            </li>
          );
        })}
      </ol>

      {!isTerminal && onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="mt-4 inline-flex items-center gap-2 rounded-xl border border-red-200 bg-white px-3 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-300 dark:border-red-500/30 dark:bg-slate-950 dark:text-red-300 dark:hover:bg-red-500/10"
        >
          <Square className="h-3.5 w-3.5 fill-current" />
          Dừng trả lời
        </button>
      )}
    </section>
  );
}
