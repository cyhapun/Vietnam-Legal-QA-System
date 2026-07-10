'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, PanelLeft, LibraryBig, Scale, Check, ChevronDown, Square, ArrowDown, X } from 'lucide-react';
import { ProviderSelector } from './ProviderSelector';
import { AdvancedSettings, AdvancedConfig } from './AdvancedSettings';
import { ChatMessage } from './ChatMessage';
import { Sidebar } from './Sidebar';
import { useChatSessions } from '@/hooks/use-chat-sessions';
import { useClickOutside } from '@/hooks/use-click-outside';
import { useAISettings } from '@/hooks/use-ai-settings';
import {
  ALL_LAWS_CATEGORY,
  LAW_CATEGORIES,
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
    updateMessage,
    updateSessionTitle,
  } = useChatSessions();

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { settings: aiSettings, setSettings: setAISettings } = useAISettings();
  const model = aiSettings.model;
  const advancedConfig: AdvancedConfig = {
    temperature: aiSettings.temperature,
    maxTokens: aiSettings.maxTokens,
    topK: aiSettings.topK,
  };
  const setModel = (nextModel: string) =>
    setAISettings(current => ({ ...current, model: nextModel }));
  const setAdvancedConfig = (config: AdvancedConfig) =>
    setAISettings(current => ({ ...current, ...config }));
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

  const [drawerContext, setDrawerContext] = useState<DocumentChunk[] | null>(null);

  const [touchStart, setTouchStart] = useState(0);
  const [touchEnd, setTouchEnd] = useState(0);

  const handleTouchStart = (e: React.TouchEvent) => setTouchStart(e.targetTouches[0].clientX);
  const handleTouchMove = (e: React.TouchEvent) => setTouchEnd(e.targetTouches[0].clientX);
  const handleTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    const distance = touchStart - touchEnd;
    if (distance > 50 && isSidebarOpen) setIsSidebarOpen(false); // Swipe left
    if (distance < -50 && !isSidebarOpen) setIsSidebarOpen(true); // Swipe right
    setTouchStart(0);
    setTouchEnd(0);
  };

  const userMessages = currentMessages.filter(m => m.role === 'user');

  useEffect(() => {
    if (!scrollContainerRef.current) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const id = entry.target.id.replace('message-', '');
            const idx = currentMessages.findIndex(m => m.id === id);
            if (idx !== -1) {
              // Find the closest preceding user message
              for (let i = idx; i >= 0; i--) {
                if (currentMessages[i].role === 'user') {
                  setActiveMessageId(currentMessages[i].id);
                  break;
                }
              }
            }
          }
        });
      },
      {
        root: scrollContainerRef.current,
        rootMargin: '-49% 0px -49% 0px', // Exact center line
      }
    );

    currentMessages.forEach(msg => {
      const el = document.getElementById(`message-${msg.id}`);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [currentMessages]);

  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
      setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50);

      if (scrollTop < 20 && userMessages.length > 0) {
        setActiveMessageId(userMessages[0].id);
      }
    }
  };

  // Auto-sync Drawer Context when activeMessageId changes (if Drawer is open)
  useEffect(() => {
    if (activeMessageId) {
      const userIndex = currentMessages.findIndex(m => m.id === activeMessageId);
      if (userIndex !== -1 && userIndex + 1 < currentMessages.length) {
        const nextMsg = currentMessages[userIndex + 1];
        if (nextMsg.role === 'assistant') {
          setDrawerContext(prev => {
            if (prev !== null) {
              if (nextMsg.contextUsed && nextMsg.contextUsed.length > 0) {
                return prev !== nextMsg.contextUsed ? nextMsg.contextUsed : prev;
              } else {
                return []; // Open but empty context
              }
            }
            return prev;
          });
        }
      }
    }
  }, [activeMessageId, currentMessages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages.length, streamingText, isLoading]);

  useClickOutside(categoryRef, useCallback(() => setIsCategoryOpen(false), []));

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleFeedbackSubmit = async (messageId: string, type: 1 | -1, reason?: string, comment?: string) => {
    if (!currentSessionId) return;
    const msgIndex = currentMessages.findIndex(m => m.id === messageId);
    if (msgIndex < 0) return;
    const aiMsg = currentMessages[msgIndex];
    let userQuery = '';
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (currentMessages[i].role === 'user') {
        userQuery = currentMessages[i].content;
        break;
      }
    }
    
    // Save locally immediately
    updateMessage(currentSessionId, messageId, { feedback: type });

    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          session_id: currentSessionId,
          user_query: userQuery,
          ai_response: aiMsg.content,
          context_used: aiMsg.contextUsed,
          feedback_type: type,
          reason,
          comment,
        }),
      });
    } catch (e) {
      console.error('Feedback error:', e);
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
    let fullContext: DocumentChunk[] = [];
    let contextUsed: DocumentChunk[] = [];
    let aborted = false;

    try {
      const apiMessages = [...currentMessages, userMessage].map(m => ({ role: m.role, content: m.content }));
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          messages: apiMessages, 
          model, 
          sessionId: currentSessionId || 'unknown',
          category: lawCategory,
          temperature: advancedConfig.temperature,
          maxTokens: advancedConfig.maxTokens,
          topK: advancedConfig.topK,
          enableQueryRewriter: aiSettings.enableQueryRewriter,
          enableReranker: aiSettings.enableReranker,
          enableSemanticCache: aiSettings.enableSemanticCache,
          enableMemory: aiSettings.enableMemory
        }),
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
              fullContext = event.data || [];
              contextUsed = fullContext;
              setStreamingContext(fullContext);
            } else if (event.type === 'token') {
              accumulated += event.text;
              
              const citedIds = Array.from(accumulated.matchAll(/<cite\s+id=["']([^"']+)["']>/g)).map(m => m[1]);
              if (citedIds.length > 0) {
                const filteredContext = fullContext.filter(ctx => 
                  ctx.metadata?.id && citedIds.includes(ctx.metadata.id as string)
                );
                setStreamingContext(filteredContext);
                contextUsed = filteredContext;
              }
              
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
    <div 
      className="flex h-screen overflow-hidden font-sans relative selection:bg-indigo-100 transition-colors bg-slate-50 dark:bg-slate-950" 
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
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
        <div className="flex items-center justify-between bg-white/80 dark:bg-slate-950/80 backdrop-blur-md z-10 absolute top-0 left-0 right-0 px-4 py-3 border-b border-gray-200/60 dark:border-slate-800/60 transition-colors">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button onClick={() => setIsSidebarOpen(true)} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors" title="Mở sidebar">
                <PanelLeft className="w-5 h-5" />
              </button>
            )}
            <span className="text-sm font-bold text-gray-800 tracking-tight md:hidden">VietLaw AI</span>
          </div>
          <div className="text-[10.5px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-widest px-3 py-1 rounded-full md:block hidden bg-indigo-50 dark:bg-indigo-500/10">
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
              <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 shadow-lg shadow-indigo-500/20" style={{ background: 'linear-gradient(135deg, #4F46E5, #2563EB)' }}>
                <Scale className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2 tracking-tight">VietLaw AI</h2>
              <p className="text-gray-400 dark:text-gray-500 max-w-sm text-base mb-10 leading-relaxed">
                Trợ lý pháp lý thông minh, sẵn sàng giải đáp mọi thắc mắc về pháp luật Việt Nam.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 max-w-2xl w-full">
                {PROMPT_STARTERS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(undefined, s.prompt)}
                    className="prompt-starter text-left px-4 py-3 rounded-2xl border border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300 dark:hover:border-indigo-500/50 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/10 hover:shadow-sm transition-all duration-200 group"
                  >
                    <span className="text-[12.5px] font-semibold text-gray-700 dark:text-gray-300 group-hover:text-indigo-700 dark:group-hover:text-indigo-400 transition-colors leading-snug block">
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
                  onRefine={(prompt) => handleSubmit(undefined, prompt)}
                  onOpenContext={setDrawerContext}
                  onFeedbackSubmit={handleFeedbackSubmit}
                />
              ))}
              {/* Streaming message realtime */}
              {streamingMessage && (
                <ChatMessage
                  key="streaming"
                  message={streamingMessage}
                  isStreaming={true}
                  onOpenContext={setDrawerContext}
                />
              )}
              {/* Skeleton chi hien khi chua co text nao */}
              {isLoading && !streamingText && <SkeletonLoader />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="absolute bottom-0 left-0 right-0 pt-10 pb-4 px-4 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent dark:from-slate-950 dark:via-slate-950">
          <div className="max-w-3xl mx-auto relative">
            {/* Scroll to bottom button */}
            {!isAtBottom && currentMessages.length > 0 && (
              <div className="absolute -top-14 left-1/2 -translate-x-1/2 z-20 fade-in slide-in-from-bottom-2 duration-200">
                <button
                  onClick={scrollToBottom}
                  className="w-10 h-10 bg-white dark:bg-slate-800 rounded-full flex items-center justify-center shadow-[0_2px_10px_rgba(0,0,0,0.1)] dark:shadow-none border border-gray-100 dark:border-slate-700 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-all hover:shadow-[0_4px_14px_rgba(0,0,0,0.12)] active:scale-95"
                  title="Cuộn xuống"
                >
                  <ArrowDown className="w-5 h-5" />
                </button>
              </div>
            )}

            <div className="relative rounded-3xl bg-white dark:bg-slate-900 border border-gray-200/80 dark:border-slate-800 shadow-xl shadow-indigo-100/30 dark:shadow-none input-glow transition-all duration-300">
              <div className="flex items-center gap-2 px-3 pt-3 pb-1">
                <div className="relative flex items-center" ref={categoryRef}>
                  <button
                    type="button"
                    onClick={() => setIsCategoryOpen(!isCategoryOpen)}
                    className="flex max-w-[230px] items-center rounded-xl border border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800 px-3 py-1.5 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 active:bg-gray-200 dark:active:bg-slate-600 md:max-w-[320px]"
                    aria-haspopup="listbox"
                    aria-expanded={isCategoryOpen}
                  >
                    <LibraryBig className="w-3.5 h-3.5 text-indigo-600 mr-2" />
                    <span className="truncate text-[12px] font-bold text-gray-700 dark:text-gray-300">{selectedLawCategory.label}</span>
                    <ChevronDown className={`w-3 h-3 text-gray-400 dark:text-gray-500 ml-1.5 transition-transform duration-200 ${isCategoryOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {isCategoryOpen && (
                    <div className="absolute bottom-full left-0 z-50 mb-2 w-[320px] max-w-[calc(100vw-2rem)] animate-in rounded-2xl border border-gray-100 dark:border-slate-800 bg-white dark:bg-slate-900 py-1 shadow-xl shadow-gray-200/50 dark:shadow-none fade-in slide-in-from-bottom-2 duration-200" role="listbox">
                      <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 border-b border-gray-50 dark:border-slate-800 mb-1">Tra cứu theo lĩnh vực</div>
                      {LAW_CATEGORIES.map(category => (
                        <button
                          key={category.id}
                          onClick={() => { setLawCategory(category.id); setIsCategoryOpen(false); }}
                          className={`flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-[12px] font-bold transition-colors ${lawCategory === category.id ? 'text-indigo-700 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-500/10' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800'}`}
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
                <div className="flex items-center gap-2">
                  <AdvancedSettings config={advancedConfig} setConfig={setAdvancedConfig} />
                  <ProviderSelector model={model} setModel={setModel} />
                </div>
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
                className="w-full resize-none bg-transparent pl-5 pr-14 py-3 focus:outline-none text-gray-700 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 leading-relaxed rounded-b-3xl text-[15px] custom-scrollbar"
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

      {/* Context Drawer */}
      <div 
        className={`absolute md:relative top-0 right-0 h-full bg-white dark:bg-slate-900 shadow-[0_0_40px_rgba(0,0,0,0.1)] dark:shadow-none transition-all duration-300 z-50 border-l border-gray-200/60 dark:border-slate-800 flex-shrink-0 overflow-hidden
          ${drawerContext ? 'translate-x-0 md:w-[400px] w-full' : 'translate-x-full md:translate-x-0 md:w-0 w-full'}`}
      >
        {drawerContext && (
          <div className="flex flex-col h-full">
            <div className="h-14 flex items-center justify-between px-4 border-b border-gray-100 dark:border-slate-800 bg-gray-50/50 dark:bg-slate-900/50 flex-shrink-0 transition-colors">
              <span className="text-[11px] font-bold uppercase tracking-widest text-indigo-700 dark:text-indigo-400">
                Văn bản pháp lý áp dụng
              </span>
              <button 
                onClick={() => setDrawerContext(null)}
                className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-slate-800 transition-colors"
                title="Đóng"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              <div className="space-y-3">
                {drawerContext.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-[13px] text-center mt-10 italic">
                    Không có văn bản pháp lý trích dẫn cho đoạn chat này.
                  </p>
                ) : (
                  drawerContext.map((ctx, idx) => {
                    const { source, dieu, khoan, diem } = ctx.metadata || {};
                    let displayText = source || 'Tài liệu pháp lý';
                    if (dieu) displayText += ` — Điều ${dieu}`;
                    if (khoan) displayText += ` (Khoản ${khoan})`;
                    if (diem) displayText += ` Điểm ${diem}`;

                    return (
                      <div key={idx} className="p-3.5 rounded-xl border border-indigo-100/50 dark:border-indigo-500/20 bg-indigo-50/30 dark:bg-slate-800/50 hover:bg-indigo-50/60 dark:hover:bg-slate-800 transition-colors">
                        <p className="text-[13px] font-bold text-indigo-800 dark:text-indigo-400 mb-2 leading-snug">{displayText}</p>
                        <p className="text-[12.5px] leading-relaxed text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                          {ctx.content}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
