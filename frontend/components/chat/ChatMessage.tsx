'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Scale, BookOpen, ChevronDown, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react';
import type { Message } from '@/lib/types';

export type { Message, DocumentChunk } from '@/lib/types';

export function ChatMessage({ message, onRefine, isStreaming }: { message: Message; onRefine?: (prompt: string) => void; isStreaming?: boolean }) {
  const isUser = message.role === 'user';
  const [showContext, setShowContext] = useState(false);
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div id={`message-${message.id}`} className={`py-5 px-4 message-animate ${isUser ? '' : 'hover:bg-slate-50/60 transition-colors duration-200'}`}>
      <div className={`max-w-4xl mx-auto flex ${isUser ? 'flex-row-reverse gap-2.5' : 'flex-row gap-4'}`}>

        {/* Avatar */}
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 rounded-full flex items-center justify-center border border-gray-200 bg-gray-100 shadow-sm">
              <User className="w-4 h-4 text-gray-500" />
            </div>
          ) : (
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center shadow-md"
              style={{ background: 'linear-gradient(135deg, #4F46E5, #2563EB)' }}
            >
              <Scale className="w-4 h-4 text-white" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className={`flex-1 min-w-0 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          {/* Bubble */}
          <div
            className={`inline-block max-w-[88%] ${
              isUser
                ? 'px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-sm text-white'
                : 'text-gray-800 w-full'
            }`}
            style={isUser ? { background: 'linear-gradient(135deg, #4F46E5, #2563EB)' } : {}}
          >
            <div className={`prose max-w-none text-[14.5px] leading-7 ${isStreaming ? 'typing-cursor' : ''} ${
              isUser
                ? 'prose-p:leading-relaxed prose-p:text-white text-white prose-p:my-0'
                : 'prose-slate prose-p:leading-7 prose-headings:text-indigo-900 prose-a:text-blue-600 prose-strong:text-gray-900 prose-li:my-0.5 prose-p:my-2'
            }`}>
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>

          {/* --- ASSISTANT ONLY UI --- */}
          {!isUser && (
            <>
              {/* Quick action row */}
              <div className="flex items-center gap-0.5 mt-1.5">
                <button
                  onClick={handleCopy}
                  title={copied ? 'Đã sao chép!' : 'Sao chép câu trả lời'}
                  className="quick-action-btn flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-gray-400"
                >
                  {copied
                    ? <Check className="w-3.5 h-3.5 text-emerald-500" />
                    : <Copy className="w-3.5 h-3.5" />
                  }
                  <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
                </button>

                {onRefine && (
                  <button
                    onClick={() => onRefine('Giải thích đơn giản hơn với ví dụ thực tế')}
                    title="Yêu cầu giải thích đơn giản hơn"
                    className="quick-action-btn flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-gray-400"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Giải thích lại</span>
                  </button>
                )}

                <div className="w-px h-3.5 bg-gray-200 mx-1" />

                <button
                  onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                  title="Câu trả lời hữu ích"
                  className={`quick-action-btn p-1.5 rounded-lg ${feedback === 'up' ? 'text-emerald-500' : 'text-gray-400'}`}
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                  title="Câu trả lời chưa tốt"
                  className={`quick-action-btn p-1.5 rounded-lg ${feedback === 'down' ? 'text-red-400' : 'text-gray-400'}`}
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Context Citations */}
              {message.contextUsed && message.contextUsed.length > 0 && (
                <div className="mt-2 w-full max-w-[88%]">
                  <button
                    type="button"
                    onClick={() => setShowContext(!showContext)}
                    className="flex items-center gap-1.5 rounded-xl border border-indigo-100 bg-indigo-50/70 px-3 py-1.5 text-[11px] font-semibold text-indigo-700 transition-all hover:border-indigo-200 hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                    aria-expanded={showContext}
                  >
                    <BookOpen className="h-3.5 w-3.5" />
                    <span>Căn cứ pháp lý</span>
                    <span className="rounded-full bg-white px-1.5 py-0.5 text-[10px] text-indigo-600 shadow-sm">
                      {message.contextUsed.length}
                    </span>
                    <ChevronDown className={`h-3 w-3 ml-0.5 transition-transform duration-200 ${showContext ? 'rotate-180' : ''}`} />
                  </button>

                  {showContext && (
                    <div className="context-panel-in mt-2 rounded-xl border border-gray-200/80 bg-white shadow-lg shadow-gray-200/40 overflow-hidden">
                      <div className="border-b border-gray-100 px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-gray-400 bg-gray-50/50">
                        Văn bản pháp lý áp dụng
                      </div>
                      <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto custom-scrollbar">
                        {message.contextUsed.map((ctx, idx) => {
                          const { source, dieu, khoan, diem } = ctx.metadata || {};
                          let displayText = source || 'Tài liệu pháp lý';
                          if (dieu) displayText += ` — Điều ${dieu}`;
                          if (khoan) displayText += ` (Khoản ${khoan})`;
                          if (diem) displayText += ` Điểm ${diem}`;

                          return (
                            <div key={idx} className="px-3 py-2.5 hover:bg-indigo-50/30 transition-colors">
                              <p className="text-[12px] font-semibold text-indigo-800 mb-1">{displayText}</p>
                              <p className="line-clamp-3 text-[11.5px] leading-relaxed text-gray-500">
                                {ctx.content}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
