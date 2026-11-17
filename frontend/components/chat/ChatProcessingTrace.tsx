'use client';

import { useId } from 'react';
import { Check, ChevronDown, Circle, Loader2, Sparkles, XCircle } from 'lucide-react';

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

const STEPS: Array<{ key: ChatProcessingStage; label: string; doneLabel: string; activeLabel: string }> = [
  { key: 'analyzing', label: 'Phân tích câu hỏi', doneLabel: 'Đã phân tích câu hỏi', activeLabel: 'Đang phân tích câu hỏi' },
  { key: 'searching', label: 'Tra cứu căn cứ pháp lý', doneLabel: 'Đã tra cứu căn cứ pháp lý', activeLabel: 'Đang tra cứu căn cứ pháp lý' },
  { key: 'selecting', label: 'Chọn lọc thông tin phù hợp', doneLabel: 'Đã chọn lọc thông tin phù hợp', activeLabel: 'Đang chọn lọc thông tin phù hợp' },
  { key: 'generating', label: 'Tổng hợp câu trả lời', doneLabel: 'Đã tổng hợp câu trả lời', activeLabel: 'Đang tổng hợp câu trả lời' },
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

function getSummary(stage: ChatProcessingStage): string {
  if (stage === 'analyzing') return 'Đang phân tích câu hỏi';
  if (stage === 'searching') return 'Đang tra cứu căn cứ pháp lý';
  if (stage === 'selecting') return 'Đang chọn lọc thông tin phù hợp';
  if (stage === 'generating') return 'Đang tổng hợp câu trả lời';
  if (stage === 'completed') return 'Tra cứu hoàn tất';
  if (stage === 'cancelled') return 'Đã dừng yêu cầu';
  if (stage === 'error') return 'Không thể hoàn tất yêu cầu';
  return 'Đang xử lý';
}

function StatusIcon({ stage }: { stage: ChatProcessingStage }) {
  if (stage === 'completed') return <Sparkles className="h-3.5 w-3.5 text-blue-500 dark:text-blue-400" />;
  if (stage === 'cancelled' || stage === 'error') return <XCircle className="h-3.5 w-3.5 text-rose-500" />;
  return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500 motion-reduce:animate-none" aria-hidden="true" />;
}

export function ChatProcessingTrace({
  stage,
  collapsed = true,
  onToggleCollapsed,
}: ChatProcessingTraceProps) {
  const componentId = useId();

  if (stage === 'idle') return null;

  const activeIndex = ORDER[stage];
  const isDone = stage === 'completed';
  const isTerminal = isDone || stage === 'cancelled' || stage === 'error';
  const detailsId = `${componentId}-processing-trace`;
  const toggleLabel = collapsed ? 'Xem quá trình' : 'Ẩn quá trình';

  // --- COLLAPSED VIEW (Gemini / ChatGPT subtle inline pill) ---
  if (collapsed) {
    return (
      <div className="mt-2 mb-1 inline-flex items-center gap-1.5" aria-live="polite">
        <div className="inline-flex items-center gap-2 rounded-full border border-slate-200/70 bg-slate-100/70 py-1 px-3 text-xs font-medium text-slate-600 shadow-sm backdrop-blur-sm transition-all hover:bg-slate-200/60 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10">
          <StatusIcon stage={stage} />
          <span className="tracking-tight">{getSummary(stage)}</span>
          {onToggleCollapsed && (
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="inline-flex shrink-0 items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] font-semibold text-blue-600 hover:text-blue-700 focus:outline-none focus-visible:ring-1 focus-visible:ring-blue-400 dark:text-blue-400 dark:hover:text-blue-300"
              aria-expanded="false"
              aria-controls={detailsId}
            >
              <span>{toggleLabel}</span>
              <ChevronDown className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // --- EXPANDED VIEW (Sleek minimalist reasoning timeline) ---
  return (
    <section
      className="mt-2.5 mb-1.5 rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3.5 shadow-sm transition-all dark:border-white/10 dark:bg-white/[0.03] backdrop-blur-sm"
      aria-live="polite"
      aria-label="Tiến trình xử lý"
      id={detailsId}
    >
      <div className="flex items-center justify-between gap-3 border-b border-slate-200/60 pb-2.5 dark:border-white/5">
        <div className="flex items-center gap-2">
          <StatusIcon stage={stage} />
          <h3 className="text-xs font-semibold text-slate-800 dark:text-slate-200">
            {getSummary(stage)}
          </h3>
        </div>

        {onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-0.5 text-xs font-medium text-slate-500 transition hover:bg-slate-200/60 hover:text-slate-700 focus:outline-none focus-visible:ring-1 focus-visible:ring-blue-400 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-200"
            aria-expanded="true"
            aria-controls={detailsId}
          >
            <span>{toggleLabel}</span>
            <ChevronDown className="h-3 w-3 rotate-180 transition-transform" />
          </button>
        )}
      </div>

      <ol className="mt-2.5 space-y-2 pl-1">
        {STEPS.map((step, index) => {
          const complete = isDone || activeIndex > index;
          const active = !isTerminal && activeIndex === index;
          return (
            <li key={step.key} className="flex items-center gap-2.5 text-xs">
              <span
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full transition-colors ${
                  complete
                    ? 'bg-emerald-500/15 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400'
                    : active
                      ? 'bg-blue-500/15 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400 ring-2 ring-blue-500/30'
                      : 'bg-slate-200/70 text-slate-400 dark:bg-slate-800 dark:text-slate-500'
                }`}
              >
                {complete ? (
                  <Check className="h-2.5 w-2.5 stroke-[2.5]" />
                ) : active ? (
                  <Loader2 className="h-2.5 w-2.5 animate-spin" />
                ) : (
                  <Circle className="h-1.5 w-1.5 fill-current" />
                )}
              </span>
              <span
                className={`transition-colors ${
                  complete
                    ? 'text-slate-600 dark:text-slate-300'
                    : active
                      ? 'font-semibold text-blue-700 dark:text-blue-300'
                      : 'text-slate-400 dark:text-slate-500'
                }`}
              >
                {complete ? step.doneLabel : active ? step.activeLabel : step.label}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
