'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Scale, BookOpen, ChevronDown, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw, Undo2 } from 'lucide-react';
import type { Message, DocumentChunk } from '@/lib/types';

export type { Message, DocumentChunk } from '@/lib/types';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onRefine?: (prompt: string) => void;
  onOpenContext?: (context: DocumentChunk[]) => void;
}

export function ChatMessage({ message, isStreaming = false, onRefine, onOpenContext }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div id={`message-${message.id}`} className={`group py-5 px-4 message-animate ${isUser ? '' : 'hover:bg-slate-50/60 dark:hover:bg-slate-800/50 transition-colors duration-200'}`}>
      <div className={`max-w-4xl mx-auto flex ${isUser ? 'flex-row-reverse gap-2.5' : 'flex-row gap-4'}`}>

        {/* Avatar */}
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 rounded-full flex items-center justify-center border border-gray-200 dark:border-slate-700 bg-gray-100 dark:bg-slate-800 shadow-sm">
              <User className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            </div>
          ) : (
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center shadow-md shadow-indigo-500/20"
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
                : 'text-gray-800 dark:text-gray-200 w-full'
            }`}
            style={isUser ? { background: 'linear-gradient(135deg, #4F46E5, #2563EB)' } : {}}
          >
            <div className={`prose dark:prose-invert max-w-none text-[14.5px] leading-7 ${isStreaming ? 'typing-cursor' : ''} ${
              isUser
                ? 'prose-p:text-white prose-strong:text-white prose-a:text-white prose-headings:text-white prose-code:text-white prose-li:text-white'
                : 'prose-p:text-gray-800 dark:prose-p:text-gray-200 prose-headings:text-gray-900 dark:prose-headings:text-gray-100 prose-strong:text-gray-900 dark:prose-strong:text-gray-100'
            }`}>
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>

          {/* --- USER ONLY UI --- */}
          {isUser && (
            <div className="flex items-center justify-end gap-1.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-full max-w-[88%] pr-1">
              <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium mr-1 tracking-wide">
                {!isNaN(Number(message.id)) ? new Date(Number(message.id)).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
              </span>
              <button
                onClick={handleCopy}
                title={copied ? 'Đã sao chép!' : 'Sao chép'}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
              {onRefine && (
                <button
                  onClick={() => onRefine(message.content)}
                  title="Gửi lại"
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <Undo2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          {/* --- ASSISTANT ONLY UI --- */}
          {!isUser && (
            <>
              {/* Quick action row */}
              <div className="flex items-center gap-0.5 mt-1.5">
                <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium mr-2 tracking-wide">
                  {!isNaN(Number(message.id)) ? new Date(Number(message.id)).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
                </span>
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
                    onClick={() => onOpenContext?.(message.contextUsed!)}
                    className="flex items-center gap-1.5 rounded-xl border border-indigo-100 bg-indigo-50/70 px-3 py-1.5 text-[11px] font-semibold text-indigo-700 transition-all hover:border-indigo-200 hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-200 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:text-indigo-300 dark:hover:bg-indigo-500/20"
                  >
                    <BookOpen className="h-3.5 w-3.5" />
                    <span>Căn cứ pháp lý</span>
                    <span className="rounded-full bg-white dark:bg-indigo-500/20 px-1.5 py-0.5 text-[10px] text-indigo-600 dark:text-indigo-300 shadow-sm">
                      {message.contextUsed.length}
                    </span>
                    <ChevronDown className={`h-3 w-3 ml-0.5 transition-transform duration-200 -rotate-90`} />
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
