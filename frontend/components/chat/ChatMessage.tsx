'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Scale, BookOpen, ChevronDown } from 'lucide-react';
import type { Message } from '@/lib/types';

// Re-export types cho backward compatibility
export type { Message, DocumentChunk } from '@/lib/types';

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const [selectedCitation, setSelectedCitation] = useState<any>(null);

  // Parse <cite id="...">...</cite> into markdown link format
  const processedContent = message.content?.replace(
    /<cite\s+id=["']([^"']+)["']>([^<]+)<\/cite>/gi, 
    '[$2](#cite-$1)'
  ) || '';

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
                          className="text-blue-600 hover:text-blue-800 font-medium underline decoration-blue-300 decoration-dashed underline-offset-4 cursor-pointer transition-colors"
                        >
                          {props.children}
                        </a>
                      );
                    }
                    return <a {...props} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer" />;
                  }
                }}
              >
                {processedContent}
              </ReactMarkdown>
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

      {/* Citation Modal */}
      {selectedCitation && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-900/40 backdrop-blur-sm transition-opacity" 
          onClick={() => setSelectedCitation(null)}
        >
          <div 
            className="bg-white rounded-xl shadow-2xl w-[90%] max-w-2xl overflow-hidden transform transition-all scale-100" 
            onClick={e => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/80">
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-600" />
                Trích dẫn pháp lý
              </h3>
              <button 
                onClick={() => setSelectedCitation(null)} 
                className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded-full hover:bg-gray-200"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
            
            <div className="p-6 max-h-[60vh] overflow-y-auto custom-scrollbar">
              <div className="mb-4">
                <div className="inline-block px-3 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded-full text-xs font-semibold mb-3">
                  {selectedCitation.metadata?.source || 'Tài liệu pháp lý'}
                </div>
                {(selectedCitation.metadata?.dieu || selectedCitation.metadata?.khoan) && (
                  <h4 className="text-md font-semibold text-gray-800 mb-2">
                    {selectedCitation.metadata?.dieu ? `Điều ${selectedCitation.metadata.dieu}` : ''}
                    {selectedCitation.metadata?.dieu && selectedCitation.metadata?.khoan ? ' - ' : ''}
                    {selectedCitation.metadata?.khoan ? `Khoản ${selectedCitation.metadata.khoan}` : ''}
                  </h4>
                )}
              </div>
              
              <div className="text-gray-600 leading-relaxed text-sm whitespace-pre-wrap bg-gray-50/50 p-4 rounded-lg border border-gray-100">
                {selectedCitation.content}
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex justify-end">
              <button 
                onClick={() => setSelectedCitation(null)} 
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
