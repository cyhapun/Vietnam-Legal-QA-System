'use client';

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import Image from 'next/image';
import ReactMarkdown from 'react-markdown';
import { User, BookOpen, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw, Undo2, Pencil, X } from 'lucide-react';
import type { Message, DocumentChunk } from '@/lib/types';
import { ChatProcessingTrace } from './ChatProcessingTrace';
import { CHAT_CONTENT_WIDTH_CLASS, CHAT_ROW_WIDTH_CLASS } from './layout';

export type { Message, DocumentChunk } from '@/lib/types';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onRefine?: (prompt: string) => void;
  onRegenerate?: (messageId: string) => void;
  onEditPrompt?: (prompt: string) => void;
  onOpenContext?: (context: DocumentChunk[]) => void;
  onFeedbackSubmit?: (messageId: string, type: 1 | -1, reason?: string, comment?: string) => void;
  onRetry?: () => void;
  isSourcesPanelOpen?: boolean;
}

export function ChatMessage({
  message,
  isStreaming = false,
  onRefine,
  onRegenerate,
  onEditPrompt,
  onFeedbackSubmit,
  onRetry,
}: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [mounted, setMounted] = useState(false);
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(
    message.feedback === 1 ? 'up' : message.feedback === -1 ? 'down' : null
  );
  const [showNegativeForm, setShowNegativeForm] = useState(false);
  const [reason, setReason] = useState('Sai luật');
  const [comment, setComment] = useState('');
  const [selectedCitation, setSelectedCitation] = useState<DocumentChunk | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    setFeedback(message.feedback === 1 ? 'up' : message.feedback === -1 ? 'down' : null);
  }, [message.feedback]);

  useEffect(() => {
    if (!selectedCitation && !showNegativeForm) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedCitation(null);
        setShowNegativeForm(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedCitation, showNegativeForm]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedbackClick = (type: 'up' | 'down') => {
    if (type === 'up') {
      setFeedback(feedback === 'up' ? null : 'up');
      setShowNegativeForm(false);
      if (feedback !== 'up' && onFeedbackSubmit) {
        onFeedbackSubmit(message.id, 1);
      }
    } else {
      if (feedback === 'down') {
        setFeedback(null);
        setShowNegativeForm(false);
      } else {
        setFeedback('down');
        setShowNegativeForm(true);
      }
    }
  };

  const submitNegativeFeedback = () => {
    if (onFeedbackSubmit) {
      onFeedbackSubmit(message.id, -1, reason, comment);
    }
    setShowNegativeForm(false);
  };

  // Parse <cite id="...">...</cite> into markdown link format
  const processedContent = message.content?.replace(
    /<cite\s+id=["']([^"']+)["']>([^<]+)<\/cite>/gi,
    '[$2](#cite-$1)'
  ) || '';

  return (
    <div id={`message-${message.id}`} className="group py-4 sm:py-5 px-3 sm:px-4 message-animate">
      <div className={`${CHAT_ROW_WIDTH_CLASS} flex ${isUser ? 'flex-row-reverse gap-2 sm:gap-2.5' : 'flex-col sm:flex-row gap-2 sm:gap-4'}`}>

        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'mt-0.5 sm:mt-1' : 'flex items-center gap-2 sm:block sm:mt-1'}`}>
          {isUser ? (
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center border border-gray-200 dark:border-white/10 bg-gray-100 dark:bg-[#1e1e1e] shadow-sm">
              <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-500 dark:text-gray-400" />
            </div>
          ) : (
            <>
              <div className="relative w-7 h-7 sm:w-8 sm:h-8 flex-shrink-0 flex items-center justify-center">
                <Image
                  src="/logo.png"
                  alt="VietLaw AI Assistant"
                  width={32}
                  height={32}
                  className="w-full h-full object-contain drop-shadow-sm"
                  unoptimized
                />
              </div>
              <span className="text-xs font-bold text-gray-700 dark:text-gray-300 tracking-tight sm:hidden">
                VietLaw AI
              </span>
            </>
          )}
        </div>

        {/* Content */}
        <div className={`flex-1 min-w-0 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          {/* Bubble */}
          <div
            className={`${
              isUser
                ? 'inline-block max-w-[88%] sm:max-w-[82%] px-4 py-3 sm:px-5 sm:py-3.5 rounded-2xl rounded-tr-sm shadow-sm text-white'
                : `${CHAT_CONTENT_WIDTH_CLASS} text-gray-800 dark:text-gray-200`
            }`}
            style={isUser ? { background: 'linear-gradient(135deg, #2563EB, #1D4ED8)' } : {}}
          >
            {message.content && (
              <div className={`prose dark:prose-invert max-w-none break-words text-[15px] leading-7 prose-p:my-2.5 sm:prose-p:my-3 prose-ul:my-2.5 sm:prose-ul:my-3 prose-ol:my-2.5 sm:prose-ol:my-3 prose-li:my-1.5 prose-headings:mb-2 prose-headings:mt-4 sm:prose-headings:mt-5 prose-h2:text-lg sm:prose-h2:text-xl prose-h3:text-base sm:prose-h3:text-lg prose-code:rounded prose-code:bg-slate-100 prose-code:px-1 prose-code:py-0.5 prose-code:break-words dark:prose-code:bg-white/10 ${isStreaming ? 'typing-cursor' : ''} ${
                isUser
                  ? 'prose-p:text-white prose-strong:text-white prose-a:text-white prose-headings:text-white prose-code:text-white prose-li:text-white'
                  : 'prose-p:text-gray-800 dark:prose-p:text-gray-200 prose-headings:text-gray-900 dark:prose-headings:text-gray-100 prose-strong:text-gray-900 dark:prose-strong:text-gray-100'
              }`}>
                <ReactMarkdown
                  components={{
                    a: ({ node, ...props }) => {
                      const href = props.href || '';
                      if (href.startsWith('#cite-')) {
                        const citeId = href.replace('#cite-', '');
                        return (
                          <a
                            {...props}
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              const citedContext = message.contextUsed?.find(c => c.metadata?.id === citeId);
                              if (citedContext) setSelectedCitation(citedContext);
                            }}
                            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium underline decoration-blue-400/60 dark:decoration-blue-500/50 decoration-dashed underline-offset-4 cursor-pointer transition-colors"
                          >
                            {props.children}
                          </a>
                        );
                      }
                      return <a {...props} className="text-blue-600 dark:text-blue-400 hover:underline break-all" target="_blank" rel="noopener noreferrer" />;
                    },
                    table: ({ node, ...props }) => (
                      <div className="my-3 w-full overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
                        <table {...props} className="min-w-full border-collapse text-sm" />
                      </div>
                    ),
                    pre: ({ node, ...props }) => (
                      <pre {...props} className="max-w-full overflow-x-auto rounded-xl p-3 text-xs sm:text-sm" />
                    ),
                  }}
                >
                  {processedContent}
                </ReactMarkdown>
              </div>
            )}

            {!isUser && !message.content?.trim() && message.processingStage && !['completed', 'generating', 'idle'].includes(message.processingStage) && (
              <ChatProcessingTrace stage={message.processingStage} />
            )}
          </div>

          {/* --- USER ONLY UI --- */}
          {isUser && (
            <div className="flex items-center justify-end gap-0.5 mt-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus-within:opacity-100 transition-opacity duration-200 w-full max-w-[88%] sm:max-w-[82%] pr-0.5">
              <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium mr-1 tracking-wide">
                {!isNaN(Number(message.id)) ? new Date(Number(message.id)).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
              </span>
              <button
                onClick={handleCopy}
                title={copied ? 'Đã sao chép!' : 'Sao chép câu hỏi'}
                aria-label="Sao chép câu hỏi"
                className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
              {(onEditPrompt || onRefine) && (
                <button
                  onClick={() => onEditPrompt ? onEditPrompt(message.content) : onRefine?.(message.content)}
                  title="Chỉnh sửa câu hỏi"
                  aria-label="Chỉnh sửa câu hỏi"
                  className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          {/* --- ASSISTANT ONLY UI --- */}
          {!isUser && (
            <div className="mt-1.5 sm:mt-2 flex flex-wrap items-center gap-0.5 opacity-90 hover:opacity-100 transition-opacity">
              <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium mr-1 tracking-wide">
                {!isNaN(Number(message.id)) ? new Date(Number(message.id)).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
              </span>
              <button
                onClick={handleCopy}
                title={copied ? 'Đã sao chép!' : 'Sao chép câu trả lời'}
                aria-label="Sao chép câu trả lời"
                className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              >
                {copied
                  ? <Check className="w-3.5 h-3.5 text-emerald-500" />
                  : <Copy className="w-3.5 h-3.5" />
                }
              </button>

              {(onRegenerate || onRefine) && !isStreaming && (
                <button
                  onClick={() => onRegenerate ? onRegenerate(message.id) : onRefine?.('Giải thích đơn giản hơn với ví dụ thực tế')}
                  title="Tạo lại câu trả lời"
                  aria-label="Tạo lại câu trả lời"
                  className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              )}

              {onRetry && (message.processingStage === 'error' || message.processingStage === 'cancelled') && (
                <button
                  onClick={onRetry}
                  title="Thử lại câu hỏi trước"
                  aria-label="Thử lại câu hỏi trước"
                  className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
                >
                  <Undo2 className="w-3.5 h-3.5" />
                </button>
              )}

              <div className="w-px h-3.5 bg-gray-200 dark:bg-white/10 mx-1" />

              <button
                onClick={() => handleFeedbackClick('up')}
                title="Câu trả lời hữu ích"
                aria-label="Câu trả lời hữu ích"
                className={`p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 hover:bg-gray-100 dark:hover:bg-white/10 ${feedback === 'up' ? 'text-emerald-500' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleFeedbackClick('down')}
                title="Báo cáo câu trả lời chưa chuẩn"
                aria-label="Báo cáo câu trả lời chưa chuẩn"
                className={`p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 hover:bg-gray-100 dark:hover:bg-white/10 ${feedback === 'down' ? 'text-red-400' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Negative Feedback Modal / Bottom Sheet via Portal */}
      {mounted && showNegativeForm && createPortal(
        <div
          className="fixed inset-0 z-[150] flex items-end sm:items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setShowNegativeForm(false)}
        >
          <div
            className="bg-white dark:bg-[#1e1e1e] border-t sm:border border-gray-200 dark:border-white/10 rounded-t-2xl sm:rounded-2xl shadow-2xl p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] sm:pb-5 w-full sm:w-[90%] sm:max-w-sm animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-gray-800 dark:text-gray-100">Vấn đề bạn gặp phải?</h4>
              <button
                type="button"
                onClick={() => setShowNegativeForm(false)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
                aria-label="Đóng biểu mẫu góp ý"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-gray-50 dark:bg-[#171717] border border-gray-200 dark:border-white/10 rounded-xl text-base sm:text-xs p-2.5 mb-2.5 text-gray-700 dark:text-gray-200 outline-none focus:border-blue-500"
            >
              <option value="Sai luật">Sai luật</option>
              <option value="Trích dẫn sai">Trích dẫn sai</option>
              <option value="Không liên quan">Không liên quan</option>
              <option value="Khác">Khác</option>
            </select>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Góp ý thêm (không bắt buộc)..."
              className="w-full bg-gray-50 dark:bg-[#171717] border border-gray-200 dark:border-white/10 rounded-xl text-base sm:text-xs p-2.5 mb-3 min-h-[80px] text-gray-700 dark:text-gray-200 outline-none focus:border-blue-500 resize-none custom-scrollbar"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowNegativeForm(false)}
                className="px-4 py-2 text-sm sm:text-xs font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-white/10 hover:bg-gray-200 dark:hover:bg-white/15 rounded-xl transition-colors"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={submitNegativeFeedback}
                className="px-4 py-2 text-sm sm:text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold transition-colors"
              >
                Gửi
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Citation Modal / Bottom Sheet via Portal */}
      {mounted && selectedCitation && createPortal(
        <div
          className="fixed inset-0 z-[150] flex items-end sm:items-center justify-center bg-gray-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
          onClick={() => setSelectedCitation(null)}
        >
          <div
            className="bg-white dark:bg-[#1e1e1e] rounded-t-2xl sm:rounded-2xl shadow-2xl w-full sm:w-[90%] sm:max-w-2xl max-h-[85dvh] flex flex-col overflow-hidden transform transition-all border-t sm:border border-gray-200 dark:border-white/10"
            onClick={e => e.stopPropagation()}
          >
            <div className="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-gray-100 dark:border-white/10 flex justify-between items-center bg-gray-50/80 dark:bg-[#171717]/60 shrink-0">
              <h3 className="text-base sm:text-lg font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0" />
                Trích dẫn pháp lý
              </h3>
              <button
                type="button"
                onClick={() => setSelectedCitation(null)}
                aria-label="Đóng trích dẫn"
                className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center text-gray-400 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors rounded-full hover:bg-gray-200 dark:hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 sm:p-6 overflow-y-auto custom-scrollbar flex-1 min-h-0">
              <div className="mb-3 sm:mb-4">
                <div className="inline-block px-3 py-1 bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-100 dark:border-blue-500/20 rounded-full text-xs font-semibold mb-2.5">
                  {selectedCitation.metadata?.source || 'Tài liệu pháp lý'}
                </div>
                {(selectedCitation.metadata?.dieu || selectedCitation.metadata?.khoan) && (
                  <h4 className="text-sm sm:text-base font-semibold text-gray-800 dark:text-gray-100 mb-2">
                    {selectedCitation.metadata?.dieu ? `Điều ${selectedCitation.metadata.dieu}` : ''}
                    {selectedCitation.metadata?.dieu && selectedCitation.metadata?.khoan ? ' - ' : ''}
                    {selectedCitation.metadata?.khoan ? `Khoản ${selectedCitation.metadata.khoan}` : ''}
                  </h4>
                )}
              </div>

              <div className="text-gray-700 dark:text-gray-300 leading-relaxed text-sm whitespace-pre-wrap break-words bg-gray-50/70 dark:bg-[#171717]/70 p-3.5 sm:p-4 rounded-xl border border-gray-100 dark:border-white/10">
                {selectedCitation.content}
              </div>
            </div>

            <div className="px-4 sm:px-6 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))] sm:py-4 border-t border-gray-100 dark:border-white/10 bg-gray-50 dark:bg-[#171717]/60 flex justify-end shrink-0">
              <button
                type="button"
                onClick={() => setSelectedCitation(null)}
                className="w-full sm:w-auto px-5 py-2.5 sm:py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl sm:rounded-lg transition-colors shadow-sm"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
