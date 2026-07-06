'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, PanelLeft, LibraryBig, Gavel, Check, ChevronDown, Square, ArrowDown } from 'lucide-react';
import { ProviderSelector } from './ProviderSelector';
import { ChatMessage } from './ChatMessage';
import { Sidebar } from './Sidebar';
import { useChatSessions } from '@/hooks/use-chat-sessions';
import { useClickOutside } from '@/hooks/use-click-outside';
import {
  ALL_LAWS_CATEGORY,
  LAW_CATEGORIES,
  DEFAULT_MODEL,
} from '@/lib/constants';
import type { Message, DocumentChunk } from '@/lib/types';

const PROMPT_STARTERS = [
  { label: 'Thủ tục làm sổ đỏ', prompt: 'Thủ tục cấp giấy chứng nhận quyền sử dụng đất (sổ đỏ) như thế nào?' },
  { label: 'Tài sản chung vợ chồng', prompt: 'Tài sản chung của vợ chồng bao gồm những gì theo Luật Hôn nhân gia đình?' },
  { label: 'Thừa kế theo pháp luật', prompt: 'Thừa kế theo pháp luật được chia như thế nào khi không có di chúc?' },
  { label: 'Hợp đồng lao động', prompt: 'Hợp đồng lao động phải có những điều khoản bắt buộc nào?' },
  { label: 'Bồi thường tai nạn', prompt: 'Người gây tai nạn giao thông phải bồi thường những khoản nào?' },
  { label: 'Thành lập công ty', prompt: 'Điều kiện và thủ tục thành lập công ty TNHH là gì?' },
];

export function ChatInterface() {
  const {
    sessions,
    currentSessionId,
    currentMessages,
    isMounted,
    handleNewChat,
    handleSelectSession,
    handleDeleteSession,
    addMessage,
    updateSessionTitle,
  } = useChatSessions();

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [lawCategory, setLawCategory] = useState(ALL_LAWS_CATEGORY);
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);
  const categoryRef = useRef<HTMLDivElement>(null);
  const selectedLawCategory =
    LAW_CATEGORIES.find(category => category.id === lawCategory) ?? LAW_CATEGORIES[0];
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Streaming state
  const [streamingText, setStreamingText] = useState('');
  const [streamingContext, setStreamingContext] = useState<DocumentChunk[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // States for mini-map
  const [activeMessageId, setActiveMessageId] = useState<string | null>(null);
  const [hoveredMessageId, setHoveredMessageId] = useState<string | null>(null);

  const userMessages = currentMessages.filter(m => m.role === 'user');

  useEffect(() => {
    if (!scrollContainerRef.current) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        // Find the most visible intersecting entry
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const id = entry.target.id.replace('message-', '');
            setActiveMessageId(id);
          }
        });
      },
      {
        root: scrollContainerRef.current,
        rootMargin: '-49% 0px -49% 0px', // Exact center line
      }
    );

    userMessages.forEach(msg => {
      const el = document.getElementById(`message-${msg.id}`);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [userMessages.length, currentMessages]);

  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
      setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages, streamingText, isLoading]);

  useClickOutside(categoryRef, useCallback(() => setIsCategoryOpen(false), []));

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  // Huy stream
  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleSubmit = async (e?: React.FormEvent, overrideText?: string) => {
    if (e) e.preventDefault();

    // Neu dang loading: Enter/Click = huy
    if (isLoading) {
      handleAbort();
      return;
    }

    const userText = (overrideText ?? input).trim();
    if (!userText || !currentSessionId) return;

    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = '52px';

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: userText };
    addMessage(userMessage);

    if (currentMessages.length === 0) {
      updateSessionTitle(userText);
    }

    setIsLoading(true);
    setStreamingText('');
    setStreamingContext([]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let accumulated = '';
    let contextUsed: DocumentChunk[] = [];
    let aborted = false;

    try {
      const apiMessages = [...currentMessages, userMessage].map(m => ({ role: m.role, content: m.content }));
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages, model, category: lawCategory }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error('Stream không khả dụng');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          try {
            const event = JSON.parse(raw);

            if (event.type === 'context') {
              contextUsed = event.data || [];
              setStreamingContext(contextUsed);
            } else if (event.type === 'token') {
              accumulated += event.text;
              setStreamingText(accumulated);
            } else if (event.type === 'done') {
              // Stream hoan tat
            } else if (event.type === 'error') {
              accumulated += '\n\nLỗi: ' + event.message;
              setStreamingText(accumulated);
            }
          } catch {
            // Ignore JSON parse errors
          }
        }
      }

      // Flush vao messages
      const finalText = aborted
        ? accumulated + '\n\n*[Đã dừng]*'
        : accumulated;

      addMessage({
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: finalText || 'Không có phản hồi từ AI.',
        contextUsed,
      });

    } catch (error: any) {
      if (error.name === 'AbortError') {
        // Nguoi dung chu dong huy
        if (accumulated) {
          addMessage({
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: accumulated + '\n\n*[Đã dừng]*',
            contextUsed,
          });
        }
      } else {
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Xin lỗi, đã có lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại Backend.',
        });
      }
    } finally {
      setIsLoading(false);
      setStreamingText('');
      setStreamingContext([]);
      abortControllerRef.current = null;
    }
  };

  const SkeletonLoader = () => (
    <div className="py-5 px-4">
      <div className="max-w-4xl mx-auto flex flex-row gap-4">
        <div className="skeleton w-8 h-8 rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-2.5 pt-1">
          <div className="skeleton h-3.5 w-3/4" />
          <div className="skeleton h-3.5 w-full" />
          <div className="skeleton h-3.5 w-5/6" />
          <div className="skeleton h-3.5 w-2/3" />
        </div>
      </div>
    </div>
  );

  // Tin nhan dang stream (hien thi realtime)
  const streamingMessage: Message | null = isLoading && streamingText
    ? {
        id: 'streaming',
        role: 'assistant',
        content: streamingText,
        contextUsed: streamingContext.length > 0 ? streamingContext : undefined,
      }
    : null;

  if (!isMounted) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: '#F8FAFC' }}>
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-indigo-100 rounded-full" />
            <div className="w-12 h-12 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0" />
          </div>
          <span className="text-gray-400 font-medium text-sm animate-pulse">Khởi tạo hệ thống...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden font-sans relative selection:bg-indigo-100" style={{ background: '#F8FAFC' }}>
      <div className={`flex-shrink-0 transition-all duration-300 ease-in-out overflow-hidden h-full z-20 ${isSidebarOpen ? 'w-64 opacity-100' : 'w-0 opacity-0'}`}>
        <div className="w-64 h-full">
          <Sidebar
            sessions={sessions}
            currentSessionId={currentSessionId}
            onNewChat={handleNewChat}
            onSelectSession={handleSelectSession}
            onDeleteSession={handleDeleteSession}
            onCloseSidebar={() => setIsSidebarOpen(false)}
          />
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 relative h-full">
        <div className="flex items-center justify-between bg-white/80 backdrop-blur-md z-10 absolute top-0 left-0 right-0 px-4 py-3 border-b border-gray-200/60">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button onClick={() => setIsSidebarOpen(true)} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors" title="Mở sidebar">
                <PanelLeft className="w-5 h-5" />
              </button>
            )}
            <span className="text-sm font-bold text-gray-800 tracking-tight md:hidden">VietLaw AI</span>
          </div>
          <div className="text-[10.5px] font-bold text-indigo-600 uppercase tracking-widest px-3 py-1 rounded-full md:block hidden" style={{ background: 'linear-gradient(90deg, #EEF2FF, #E0E7FF)' }}>
            Hệ thống tra cứu pháp luật thông minh
          </div>
        </div>

        {/* History Mini-map Stack */}
        {userMessages.length > 0 && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2 z-30 group hidden md:flex items-center">
            {/* The Tooltip / Popup */}
            <div className="absolute right-full pr-4 py-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 pointer-events-none group-hover:pointer-events-auto z-50">
              <div className="bg-white border border-gray-200/60 shadow-[0_10px_40px_-10px_rgba(0,0,0,0.15)] rounded-2xl w-72 max-h-[60vh] overflow-hidden flex flex-col relative">
                <div className="overflow-y-auto custom-scrollbar p-2 relative z-10 bg-white">
                  {userMessages.map(msg => (
                    <button
                      key={msg.id}
                      onMouseEnter={() => setHoveredMessageId(msg.id)}
                      onMouseLeave={() => setHoveredMessageId(null)}
                      onClick={() => {
                        setActiveMessageId(msg.id);
                        document.getElementById(`message-${msg.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      }}
                      className={`w-full text-left px-3 py-2.5 text-[13px] font-medium rounded-xl truncate transition-colors mb-0.5 last:mb-0 ${
                        activeMessageId === msg.id 
                          ? 'text-indigo-700 bg-indigo-50/80' 
                          : 'text-gray-700 hover:text-indigo-700 hover:bg-indigo-50/50'
                      }`}
                      title={msg.content}
                    >
                      {msg.content}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* The Stack Lines */}
            <div className="flex flex-col items-center justify-center gap-1.5 py-4 w-8 cursor-pointer">
              {userMessages.map((msg, i) => {
                const isActive = msg.id === activeMessageId;
                const isHovered = msg.id === hoveredMessageId;
                const isHighlight = isActive || isHovered;
                return (
                  <div 
                    key={msg.id} 
                    className={`h-[2px] rounded-full transition-all duration-300 ${
                      isHighlight 
                        ? 'bg-indigo-600 w-6' 
                        : 'bg-gray-300 w-4 group-hover:bg-indigo-300 group-hover:w-5'
                    }`} 
                  />
                );
              })}
            </div>
          </div>
        )}

        <div 
          className="flex-1 overflow-y-auto pt-16 pb-40 custom-scrollbar" 
          ref={scrollContainerRef}
          onScroll={handleScroll}
        >
          {currentMessages.length === 0 && !streamingMessage ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 shadow-lg" style={{ background: 'linear-gradient(135deg, #4F46E5, #2563EB)' }}>
                <Gavel className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-gray-800 mb-2 tracking-tight">VietLaw AI</h2>
              <p className="text-gray-400 max-w-sm text-base mb-10 leading-relaxed">
                Trợ lý pháp lý thông minh, sẵn sàng giải đáp mọi thắc mắc về pháp luật Việt Nam.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 max-w-2xl w-full">
                {PROMPT_STARTERS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(undefined, s.prompt)}
                    className="prompt-starter text-left px-4 py-3 rounded-2xl border border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/50 hover:shadow-sm transition-all duration-200 group"
                  >
                    <span className="text-[12.5px] font-semibold text-gray-700 group-hover:text-indigo-700 transition-colors leading-snug block">
                      {s.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="pb-8">
              {currentMessages.map(msg => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onRefine={msg.role === 'assistant' ? (prompt) => handleSubmit(undefined, prompt) : undefined}
                />
              ))}
              {/* Streaming message realtime */}
              {streamingMessage && (
                <ChatMessage
                  key="streaming"
                  message={streamingMessage}
                  isStreaming={true}
                />
              )}
              {/* Skeleton chi hien khi chua co text nao */}
              {isLoading && !streamingText && <SkeletonLoader />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="absolute bottom-0 left-0 right-0 pt-10 pb-4 px-4" style={{ background: 'linear-gradient(to top, #F8FAFC 70%, transparent)' }}>
          <div className="max-w-3xl mx-auto relative">
            {/* Scroll to bottom button */}
            {!isAtBottom && currentMessages.length > 0 && (
              <div className="absolute -top-14 left-1/2 -translate-x-1/2 z-20 fade-in slide-in-from-bottom-2 duration-200">
                <button
                  onClick={scrollToBottom}
                  className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-[0_2px_10px_rgba(0,0,0,0.1)] border border-gray-100 text-gray-600 hover:text-gray-900 transition-all hover:shadow-[0_4px_14px_rgba(0,0,0,0.12)] active:scale-95"
                  title="Cuộn xuống"
                >
                  <ArrowDown className="w-5 h-5" />
                </button>
              </div>
            )}

            <div className="relative rounded-3xl bg-white border border-gray-200/80 shadow-xl shadow-indigo-100/30 input-glow transition-all duration-300">
              <div className="flex items-center gap-2 px-3 pt-3 pb-1">
                <div className="relative flex items-center" ref={categoryRef}>
                  <button
                    type="button"
                    onClick={() => setIsCategoryOpen(!isCategoryOpen)}
                    className="flex max-w-[230px] items-center rounded-xl border border-gray-100 bg-gray-50 px-3 py-1.5 transition-colors hover:bg-gray-100 active:bg-gray-200 md:max-w-[320px]"
                    aria-haspopup="listbox"
                    aria-expanded={isCategoryOpen}
                  >
                    <LibraryBig className="w-3.5 h-3.5 text-indigo-600 mr-2" />
                    <span className="truncate text-[12px] font-bold text-gray-700">{selectedLawCategory.label}</span>
                    <ChevronDown className={`w-3 h-3 text-gray-400 ml-1.5 transition-transform duration-200 ${isCategoryOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {isCategoryOpen && (
                    <div className="absolute bottom-full left-0 z-50 mb-2 w-[320px] max-w-[calc(100vw-2rem)] animate-in rounded-2xl border border-gray-100 bg-white py-1 shadow-xl shadow-gray-200/50 fade-in slide-in-from-bottom-2 duration-200" role="listbox">
                      <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 border-b border-gray-50 mb-1">Tra cứu theo lĩnh vực</div>
                      {LAW_CATEGORIES.map(category => (
                        <button
                          key={category.id}
                          onClick={() => { setLawCategory(category.id); setIsCategoryOpen(false); }}
                          className={`flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-[12px] font-bold transition-colors ${lawCategory === category.id ? 'text-indigo-700 bg-indigo-50/50' : 'text-gray-600 hover:bg-gray-50'}`}
                          role="option"
                          aria-selected={lawCategory === category.id}
                        >
                          <span className="truncate">{category.label}</span>
                          {lawCategory === category.id && <Check className="h-4 w-4 flex-shrink-0 text-indigo-600" />}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <ProviderSelector model={model} setModel={setModel} />
              </div>

              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInput}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                placeholder={isLoading ? 'Nhấn Enter để dừng...' : 'Nhập câu hỏi pháp lý... (Shift + Enter xuống dòng)'}
                className="w-full resize-none bg-transparent pl-5 pr-14 py-3 focus:outline-none text-gray-700 leading-relaxed rounded-b-3xl text-[15px] custom-scrollbar"
                rows={1}
                style={{ minHeight: '52px', maxHeight: '160px' }}
              />

              {/* Nut Send / Stop */}
              {isLoading ? (
                <button
                  onClick={handleAbort}
                  title="Dừng tạo câu trả lời (Enter)"
                  className="absolute right-3 bottom-3 p-2.5 text-white rounded-2xl transition-all shadow-md active:scale-95 flex items-center justify-center animate-pulse"
                  style={{ background: 'linear-gradient(135deg, #EF4444, #DC2626)' }}
                >
                  <Square className="w-4 h-4 fill-white" />
                </button>
              ) : (
                <button
                  onClick={(e) => handleSubmit(e as any)}
                  disabled={!input.trim()}
                  className={`absolute right-3 bottom-3 p-2.5 text-white rounded-2xl disabled:opacity-40 transition-all shadow-md active:scale-95 flex items-center justify-center ${input.trim() ? 'send-btn-ready' : ''}`}
                  style={{ background: 'linear-gradient(135deg, #4F46E5, #2563EB)' }}
                >
                  <Send className="w-4 h-4 translate-x-px translate-y-px" />
                </button>
              )}
            </div>
            <p className="text-center mt-2.5 text-[10px] text-gray-400 font-medium">
              AI có thể cung cấp thông tin không chính xác. Hãy luôn kiểm tra lại dữ liệu quan trọng.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
