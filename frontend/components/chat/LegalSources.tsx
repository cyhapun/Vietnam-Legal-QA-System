'use client';

import { useMemo, useState } from 'react';
import { BookOpen, Check, ChevronDown, Copy } from 'lucide-react';
import type { DocumentChunk } from '@/lib/types';

interface LegalSourcesProps {
  sources?: DocumentChunk[];
  compact?: boolean;
  onOpenAll?: (sources: DocumentChunk[]) => void;
}

function sourceKey(source: DocumentChunk, index: number): string {
  return String(source.metadata?.id || `${source.metadata?.source || 'source'}-${index}`);
}

function buildTitle(source: DocumentChunk): string {
  return source.metadata?.source || source.metadata?.law || 'Tài liệu pháp lý';
}

function buildMeta(source: DocumentChunk): string {
  const parts = [];
  if (source.metadata?.dieu) parts.push(`Điều ${source.metadata.dieu}`);
  if (source.metadata?.khoan) parts.push(`Khoản ${source.metadata.khoan}`);
  if (source.metadata?.diem) parts.push(`Điểm ${source.metadata.diem}`);
  return parts.join(' · ');
}

function excerpt(text: string, expanded: boolean): string {
  if (expanded || text.length <= 260) return text;
  return `${text.slice(0, 260).trim()}...`;
}

export function LegalSources({ sources = [], compact = false, onOpenAll }: LegalSourcesProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const deduped = useMemo(() => {
    const seen = new Set<string>();
    return sources.filter((source, index) => {
      const key = sourceKey(source, index);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [sources]);

  if (deduped.length === 0) return null;

  const copyCitation = async (source: DocumentChunk, key: string) => {
    const meta = [buildTitle(source), buildMeta(source)].filter(Boolean).join(' — ');
    await navigator.clipboard.writeText(`${meta}\n\n${source.content}`);
    setCopiedKey(key);
    window.setTimeout(() => setCopiedKey(null), 1800);
  };

  return (
    <section className="mt-4 w-full" aria-label="Căn cứ pháp lý">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="inline-flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
          <BookOpen className="h-4 w-4 text-blue-700 dark:text-blue-300" />
          Căn cứ pháp lý
        </h3>
        {onOpenAll && (
          <button
            type="button"
            onClick={() => onOpenAll(deduped)}
            className="rounded-lg px-2 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:text-blue-300 dark:hover:bg-blue-500/10"
          >
            Mở bảng bên
          </button>
        )}
      </div>
      <div className={`grid gap-2 ${compact ? '' : 'md:grid-cols-2'}`}>
        {deduped.map((source, index) => {
          const key = sourceKey(source, index);
          const isExpanded = expanded[key] ?? false;
          const meta = buildMeta(source);
          const canExpand = source.content.length > 260;
          return (
            <article
              key={key}
              className="rounded-xl border border-slate-200 bg-white p-3 text-left shadow-sm transition hover:border-blue-200 dark:border-white/10 dark:bg-slate-950/40 dark:hover:border-blue-500/30"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h4 className="truncate text-sm font-bold text-slate-900 dark:text-slate-100">
                    {buildTitle(source)}
                  </h4>
                  {meta && (
                    <p className="mt-1 text-xs font-semibold text-blue-700 dark:text-blue-300">
                      {meta}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => copyCitation(source, key)}
                  className="shrink-0 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:hover:bg-white/10 dark:hover:text-blue-300"
                  aria-label="Sao chép trích dẫn"
                  title={copiedKey === key ? 'Đã sao chép' : 'Sao chép trích dẫn'}
                >
                  {copiedKey === key ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>

              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-300">
                “{excerpt(source.content, isExpanded)}”
              </p>

              {canExpand && (
                <button
                  type="button"
                  onClick={() => setExpanded(current => ({ ...current, [key]: !isExpanded }))}
                  className="mt-2 inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 dark:text-blue-300 dark:hover:bg-blue-500/10"
                  aria-expanded={isExpanded}
                >
                  {isExpanded ? 'Thu gọn' : 'Xem nội dung'}
                  <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
