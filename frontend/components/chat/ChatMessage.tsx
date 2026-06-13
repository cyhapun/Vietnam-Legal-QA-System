import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Scale, BookOpen, ChevronDown } from 'lucide-react';
import type { Message } from '@/lib/types';

// Re-export types cho backward compatibility
export type { Message, DocumentChunk } from '@/lib/types';

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`py-6 px-4 transition-all hover:bg-gray-50/50 ${isUser ? '' : ''}`}>
      <div className={`max-w-4xl mx-auto flex ${isUser ? 'flex-row-reverse gap-2.5' : 'flex-row gap-5'}`}>
        
        {/* Avatar */}
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center shadow-inner border border-gray-300">
              <User className="w-5 h-5 text-gray-600" />
            </div>
          ) : (
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center shadow-md border border-blue-800">
              <Scale className="w-4 h-4 text-white" />
            </div>
          )}
        </div>
        
        {/* Message Content */}
        <div className={`flex-1 min-w-0 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div className={`inline-block max-w-[85%] ${
            isUser 
              ? 'bg-blue-600 text-white px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-sm' 
              : 'text-gray-800'
          }`}>
            <div className={`prose max-w-none ${
              isUser 
                ? 'prose-p:leading-relaxed prose-p:text-white text-white' 
                : 'prose-slate prose-p:leading-7 prose-headings:text-indigo-900 prose-a:text-blue-600 prose-strong:text-gray-900'
            }`}>
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>
          
          {/* RAG Context Display (Căn cứ pháp lý) */}
          {!isUser && message.contextUsed && message.contextUsed.length > 0 && (
            <div className="group/sources relative mt-3">
              <button
                type="button"
                className="flex items-center gap-1.5 rounded-lg border border-indigo-100 bg-indigo-50/60 px-2.5 py-1.5 text-[11px] font-semibold text-indigo-700 transition-colors hover:border-indigo-200 hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                aria-label={`Hiển thị ${message.contextUsed.length} căn cứ pháp lý`}
              >
                <BookOpen className="h-3.5 w-3.5" />
                <span>Căn cứ pháp lý</span>
                <span className="rounded-full bg-white px-1.5 py-0.5 text-[10px] text-indigo-600 shadow-sm">
                  {message.contextUsed.length}
                </span>
                <ChevronDown className="h-3 w-3 transition-transform group-hover/sources:rotate-180 group-focus-within/sources:rotate-180" />
              </button>

              <div className="pointer-events-none invisible absolute left-0 top-full z-30 w-[min(520px,calc(100vw-3rem))] pt-2 opacity-0 transition-all duration-150 group-hover/sources:pointer-events-auto group-hover/sources:visible group-hover/sources:opacity-100 group-focus-within/sources:pointer-events-auto group-focus-within/sources:visible group-focus-within/sources:opacity-100">
                <div className="max-h-80 overflow-y-auto rounded-xl border border-gray-200 bg-white p-2 shadow-xl shadow-gray-200/60 custom-scrollbar">
                  <div className="border-b border-gray-100 px-2 pb-2 pt-1 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                    Căn cứ pháp lý áp dụng
                  </div>
                  <div className="divide-y divide-gray-100">
                    {message.contextUsed.map((ctx, idx) => {
                      const { source, dieu, khoan, diem } = ctx.metadata || {};
                      let displayText = source || 'Tài liệu pháp lý';
                      if (dieu) displayText += ` - Điều ${dieu}`;
                      if (khoan) displayText += ` (Khoản ${khoan})`;
                      if (diem) displayText += ` Điểm ${diem}`;

                      return (
                        <div key={idx} className="px-2 py-2.5">
                          <p className="text-[12px] font-semibold text-indigo-800">
                            {displayText}
                          </p>
                          <p className="mt-1 line-clamp-3 text-[11px] leading-4 text-gray-500">
                            {ctx.content}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
