'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, PanelLeft, LibraryBig, Check, ChevronDown, Square, ArrowDown } from 'lucide-react';
import { ProviderSelector } from './ProviderSelector';
import { ChatMessage } from './ChatMessage';
import { Sidebar } from './Sidebar';
import { ChatEmptyState } from './ChatEmptyState';
import type { ChatProcessingStage } from './ChatProcessingTrace';
import { CHAT_CONTENT_WIDTH_CLASS, CHAT_ROW_WIDTH_CLASS } from './layout';
import { useChatSessions } from '@/hooks/use-chat-sessions';
import { useClickOutside } from '@/hooks/use-click-outside';
import {
  ALL_LAWS_CATEGORY,
  CHAT_STORAGE_MODE,
  DEFAULT_MODEL,
  LAW_CATEGORIES,
} from '@/lib/constants';
import type { Message, DocumentChunk } from '@/lib/types';

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
    removeMessage,
    updateSessionTitle,
    isSessionLoading,
    isSessionsListLoading,
  } = useChatSessions();

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const model = DEFAULT_MODEL;
  const [lawCategory, setLawCategory] = useState(ALL_LAWS_CATEGORY);
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);
  const categoryRef = useRef<HTMLDivElement>(null);
  const selectedLawCategory =
    LAW_CATEGORIES.find(category => category.id === lawCategory) ?? LAW_CATEGORIES[0];
  const DESKTOP_BREAKPOINT = 1024;
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Sync default sidebar visibility with desktop breakpoint (closed on mobile/tablet, open on desktop)
  useEffect(() => {
    const mql = window.matchMedia(`(min-width: ${DESKTOP_BREAKPOINT}px)`);
    setIsSidebarOpen(mql.matches);
    const handleViewportChange = (event: MediaQueryListEvent) => {
      setIsSidebarOpen(event.matches);
    };
    mql.addEventListener('change', handleViewportChange);
    return () => mql.removeEventListener('change', handleViewportChange);
  }, []);

  // Streaming state
  const [streamingText, setStreamingText] = useState('');
  const [streamingContext, setStreamingContext] = useState<DocumentChunk[]>([]);
  const [processingStage, setProcessingStage] = useState<ChatProcessingStage>('idle');
  const abortControllerRef = useRef<AbortController | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // States for mini-map
  const [activeMessageId, setActiveMessageId] = useState<string | null>(null);
  const [hoveredMessageId, setHoveredMessageId] = useState<string | null>(null);

  // Ref-based edge-locked swipe tracking (prevents conflicts with vertical scroll & text selection)
  const touchOriginRef = useRef<{ x: number; y: number } | null>(null);
  const touchCurrentRef = useRef<{ x: number; y: number } | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    if (window.innerWidth >= DESKTOP_BREAKPOINT || e.targetTouches.length !== 1) {
      touchOriginRef.current = null;
      return;
    }
    const touch = e.targetTouches[0];
    touchOriginRef.current = { x: touch.clientX, y: touch.clientY };
    touchCurrentRef.current = null;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!touchOriginRef.current || e.targetTouches.length !== 1) return;
    const touch = e.targetTouches[0];
    touchCurrentRef.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTouchEnd = () => {
    const start = touchOriginRef.current;
    const end = touchCurrentRef.current;
    touchOriginRef.current = null;
    touchCurrentRef.current = null;
    if (!start || !end) return;

    const deltaX = end.x - start.x;
    const deltaY = end.y - start.y;
    const isPredominantlyHorizontal = Math.abs(deltaX) > Math.abs(deltaY) * 1.8;
    if (!isPredominantlyHorizontal) return;

    if (!isSidebarOpen && start.x <= 36 && deltaX > 64) {
      setIsSidebarOpen(true);
    } else if (isSidebarOpen && deltaX < -64) {
      setIsSidebarOpen(false);
    }
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages.length, streamingText, isLoading]);

  useClickOutside(categoryRef, useCallback(() => setIsCategoryOpen(false), []));

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const nextHeight = Math.min(el.scrollHeight, 160);
    el.style.height = `${nextHeight}px`;
    el.style.overflowY = el.scrollHeight > 160 ? 'auto' : 'hidden';
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };

  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setProcessingStage('cancelled');
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

    if (CHAT_STORAGE_MODE === 'browser') {
      return;
    }

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

  const executeStream = async ({
    apiMessages,
    userMessageId,
  }: {
    apiMessages: Array<{ role: string; content: string }>;
    userMessageId: string;
  }) => {
    if (!currentSessionId) return;

    setIsLoading(true);
    setStreamingText('');
    setStreamingContext([]);
    setProcessingStage('analyzing');

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let accumulated = '';
    let fullContext: DocumentChunk[] = [];
    let contextUsed: DocumentChunk[] = [];
    let aborted = false;
    let streamErrorMessage = '';

    try {
      setProcessingStage('searching');
      const sessionTitle = sessions.find(s => s.id === currentSessionId)?.title || 'Cuộc trò chuyện mới';
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: apiMessages,
          model,
          sessionId: currentSessionId || 'unknown',
          sessionTitle,
          messageId: userMessageId,
          category: lawCategory,
          streaming: true,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error('Phản hồi từ máy chủ không khả dụng');
      }

      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await response.json();
        if (data.sessionTitle) {
          updateSessionTitle(data.sessionTitle);
        }
        accumulated = data.text || '';
        contextUsed = (data.contextUsed || []).slice(0, 5);
        setProcessingStage('completed');
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: accumulated || 'Không có phản hồi từ AI.',
          contextUsed,
          processingStage: 'completed',
        });
        return;
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

            if (event.type === 'title' && event.title) {
              updateSessionTitle(event.title);
            } else if (event.type === 'context') {
              fullContext = event.data || [];
              contextUsed = fullContext;
              setStreamingContext(fullContext);
              setProcessingStage('selecting');
            } else if (event.type === 'token') {
              accumulated += event.text;
              setProcessingStage('generating');

              const citedIds = Array.from(accumulated.matchAll(/<cite\s+id=["']([^"']+)["']>/g)).map(m => m[1]).slice(0, 5);
              if (citedIds.length > 0) {
                const filteredContext = fullContext.filter(ctx =>
                  ctx.metadata?.id && citedIds.includes(ctx.metadata.id as string)
                );
                if (filteredContext.length > 0) {
                  setStreamingContext(filteredContext);
                  contextUsed = filteredContext;
                }
              }

              setStreamingText(accumulated);
            } else if (event.type === 'done') {
              setProcessingStage('completed');
            } else if (event.type === 'error') {
              streamErrorMessage = event.message || 'stream-error';
              setProcessingStage('error');
            }
          } catch {
            // Ignore JSON parse errors
          }
        }
      }

      // Persist final assistant turn
      const finalText = aborted
        ? `${accumulated}${accumulated ? '\n\n' : ''}Đã dừng yêu cầu.`
        : streamErrorMessage
          ? accumulated || (contextUsed.length > 0
              ? 'Đã tìm thấy căn cứ pháp lý nhưng chưa thể tổng hợp câu trả lời. Bạn vẫn có thể xem các căn cứ bên dưới.'
              : 'Không thể hoàn tất câu trả lời lúc này. Vui lòng thử lại.')
          : accumulated;

      addMessage({
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: finalText || 'Không có phản hồi từ AI.',
        contextUsed,
        processingStage: streamErrorMessage ? 'error' : aborted ? 'cancelled' : 'completed',
      });

    } catch (error: unknown) {
      const isAbort = error instanceof DOMException
        ? error.name === 'AbortError'
        : error instanceof Error && error.name === 'AbortError';

      aborted = isAbort;
      if (isAbort) {
        setProcessingStage('cancelled');
        if (accumulated) {
          addMessage({
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `${accumulated}\n\nĐã dừng yêu cầu.`,
            contextUsed,
            processingStage: 'cancelled',
          });
        } else {
          addMessage({
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: 'Đã dừng yêu cầu.',
            contextUsed,
            processingStage: 'cancelled',
          });
        }
      } else {
        setProcessingStage('error');
        const content = contextUsed.length > 0
          ? 'Đã tìm thấy căn cứ pháp lý nhưng chưa thể tổng hợp câu trả lời. Bạn vẫn có thể xem các căn cứ bên dưới.'
          : 'Không thể hoàn tất câu trả lời lúc này. Vui lòng thử lại.';
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content,
          contextUsed,
          processingStage: 'error',
        });
      }
    } finally {
      setIsLoading(false);
      setStreamingText('');
      setStreamingContext([]);
      setProcessingStage('idle');
      abortControllerRef.current = null;
    }
  };

  const handleSubmit = async (e?: React.FormEvent, overrideText?: string) => {
    if (e) e.preventDefault();

    // Cancel active stream on Enter/Click while loading
    if (isLoading) {
      handleAbort();
      return;
    }

    const userText = (overrideText ?? input).trim();
    if (!userText || !currentSessionId) return;

    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.overflowY = 'hidden';
    }

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: userText };
    addMessage(userMessage);

    if (currentMessages.length === 0) {
      updateSessionTitle(userText.length > 40 ? userText.substring(0, 40) + '...' : userText);
    }

    const apiMessages = [...currentMessages, userMessage].map(m => ({ role: m.role, content: m.content }));
    await executeStream({
      apiMessages,
      userMessageId: userMessage.id,
    });
  };

  const handleRegenerate = async (messageId: string) => {
    if (isLoading || !currentSessionId) return;

    const aiIndex = currentMessages.findIndex(m => m.id === messageId);
    if (aiIndex === -1) return;

    // Find preceding user message
    let userMsg: Message | undefined;
    let userIndex = -1;
    for (let i = aiIndex - 1; i >= 0; i--) {
      if (currentMessages[i].role === 'user') {
        userMsg = currentMessages[i];
        userIndex = i;
        break;
      }
    }

    if (!userMsg) return;

    // Remove the old AI response in-place
    removeMessage(currentSessionId, messageId);

    // Messages up to the relevant user prompt
    const contextMessages = currentMessages.slice(0, userIndex + 1);
    const apiMessages = contextMessages.map(m => ({ role: m.role, content: m.content }));

    await executeStream({
      apiMessages,
      userMessageId: userMsg.id,
    });
  };

  const handleEditPrompt = (promptText: string) => {
    setInput(promptText);
    if (textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  const SessionSkeletonLoader = () => (
    <div className="animate-pulse flex flex-col gap-6 py-5 px-4 max-w-4xl mx-auto">
      {/* Fake User Message */}
      <div className="flex justify-end gap-3 w-full mt-4">
        <div className="h-10 w-64 bg-gray-200/80 dark:bg-gray-800/80 rounded-2xl rounded-tr-sm"></div>
        <div className="h-8 w-8 bg-gray-200/80 dark:bg-gray-800/80 rounded-full flex-shrink-0"></div>
      </div>

      {/* Fake AI Message */}
      <div className="flex justify-start gap-3 w-full">
        <div className="h-8 w-8 bg-blue-100/80 dark:bg-blue-900/40 rounded-full flex-shrink-0"></div>
        <div className="space-y-3 pt-1">
          <div className="h-3.5 w-64 bg-gray-200/80 dark:bg-gray-800/80 rounded"></div>
          <div className="h-3.5 w-48 bg-gray-200/80 dark:bg-gray-800/80 rounded"></div>
          <div className="h-3.5 w-80 bg-gray-200/80 dark:bg-gray-800/80 rounded"></div>
        </div>
      </div>
    </div>
  );

  // Active streaming assistant placeholder
  const streamingMessage: Message | null = isLoading
    ? {
        id: 'streaming',
        role: 'assistant',
        content: streamingText,
        contextUsed: streamingContext.length > 0 ? streamingContext : undefined,
        processingStage,
      }
    : null;

  if (!isMounted) {
    return (
      <div className="h-dvh flex items-center justify-center bg-slate-50 dark:bg-[#171717] transition-colors">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-blue-100 dark:border-blue-950 rounded-full" />
            <div className="w-12 h-12 border-4 border-blue-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0" />
          </div>
          <span className="text-gray-400 dark:text-gray-500 font-medium text-sm animate-pulse">Khởi tạo hệ thống...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex h-dvh w-full overflow-hidden font-sans relative selection:bg-blue-100 dark:selection:bg-blue-500/30 transition-colors bg-slate-50 dark:bg-[#171717]"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {isSidebarOpen && (
        <button
          type="button"
          aria-label="Đóng danh sách hội thoại"
          className="fixed inset-0 z-30 bg-slate-950/40 backdrop-blur-[2px] lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <div className={`fixed inset-y-0 left-0 z-40 h-full overflow-hidden transition-all duration-300 ease-in-out lg:relative lg:z-20 lg:flex-shrink-0 ${
        isSidebarOpen
          ? 'w-[82vw] max-w-[300px] lg:w-64 lg:max-w-none translate-x-0 opacity-100 pointer-events-auto shadow-2xl lg:shadow-none'
          : 'w-0 -translate-x-full lg:translate-x-0 opacity-0 pointer-events-none'
      }`}>
        <div className="h-full w-[82vw] max-w-[300px] lg:w-64 lg:max-w-none">
          <Sidebar
            sessions={sessions}
            currentSessionId={currentSessionId}
            onNewChat={() => {
              handleNewChat();
              if (window.innerWidth < DESKTOP_BREAKPOINT) setIsSidebarOpen(false);
            }}
            onSelectSession={(id) => {
              handleSelectSession(id);
              if (window.innerWidth < DESKTOP_BREAKPOINT) setIsSidebarOpen(false);
            }}
            onDeleteSession={handleDeleteSession}
            onCloseSidebar={() => setIsSidebarOpen(false)}
            isSessionsListLoading={isSessionsListLoading}
          />
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 relative h-full">
        <div className="flex items-center justify-between gap-2 bg-white/85 dark:bg-[#171717]/85 backdrop-blur-md z-10 absolute top-0 left-0 right-0 px-3 sm:px-4 pt-[max(0.625rem,env(safe-area-inset-top))] pb-2.5 border-b border-gray-200/60 dark:border-white/10 transition-colors">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-2 min-h-[40px] min-w-[40px] flex items-center justify-center hover:bg-gray-100 dark:hover:bg-white/10 rounded-xl text-gray-600 dark:text-gray-300 transition-colors shrink-0"
                title="Mở sidebar"
                aria-label="Mở danh sách hội thoại"
              >
                <PanelLeft className="w-5 h-5" />
              </button>
            )}
            <span className="text-sm font-bold text-gray-800 dark:text-white tracking-tight truncate lg:hidden">VietLaw AI</span>
          </div>
          <div className="text-[10.5px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-widest px-3 py-1 rounded-full hidden lg:block bg-blue-50 dark:bg-blue-500/10 whitespace-nowrap">
            Hệ thống tra cứu pháp luật thông minh
          </div>
          {CHAT_STORAGE_MODE === 'browser' && (
            <div
              className="text-[10px] font-medium text-slate-500 dark:text-slate-400 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-white/10 whitespace-nowrap shrink-0"
              title="Lịch sử chỉ lưu trên thiết bị này"
            >
              <span className="sm:hidden">Lưu cục bộ</span>
              <span className="hidden sm:inline">Lịch sử chỉ lưu trên thiết bị này</span>
            </div>
          )}
        </div>

        {/* History Mini-map Stack */}
        {userMessages.length > 0 && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2 z-30 group hidden xl:flex items-center">
            {/* The Tooltip / Popup */}
            <div className="absolute right-full pr-4 py-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 pointer-events-none group-hover:pointer-events-auto z-50">
              <div className="bg-white dark:bg-[#1f1f1f] border border-gray-200/60 dark:border-white/10 shadow-[0_10px_40px_-10px_rgba(0,0,0,0.18)] rounded-2xl w-72 max-h-[60dvh] overflow-hidden flex flex-col relative">
                <div className="overflow-y-auto custom-scrollbar p-2 relative z-10 bg-white dark:bg-[#1f1f1f]">
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
                          ? 'text-blue-700 dark:text-blue-300 bg-blue-50/80 dark:bg-blue-500/15'
                          : 'text-gray-700 dark:text-gray-300 hover:text-blue-700 dark:hover:text-blue-300 hover:bg-blue-50/50 dark:hover:bg-white/5'
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
              {userMessages.map((msg) => {
                const isActive = msg.id === activeMessageId;
                const isHovered = msg.id === hoveredMessageId;
                const isHighlight = isActive || isHovered;
                return (
                  <div
                    key={msg.id}
                    className={`h-[2px] rounded-full transition-all duration-300 ${
                      isHighlight
                        ? 'bg-blue-600 dark:bg-blue-400 w-6'
                        : 'bg-gray-300 dark:bg-gray-600 w-4 group-hover:bg-blue-300 dark:group-hover:bg-blue-500 group-hover:w-5'
                    }`}
                  />
                );
              })}
            </div>
          </div>
        )}

        <div
          className="flex-1 overflow-y-auto pt-16 pb-44 sm:pb-40 custom-scrollbar"
          ref={scrollContainerRef}
          onScroll={handleScroll}
        >
          {currentMessages.length === 0 && !streamingMessage && !isSessionLoading ? (
            <ChatEmptyState onSelectSuggestion={prompt => setInput(prompt)} />
          ) : (
            <div className="pb-8">
              {isSessionLoading ? (
                <SessionSkeletonLoader />
              ) : (
                <>
                  {currentMessages.map((msg, index) => {
                    const previousUser = msg.role === 'assistant'
                      ? [...currentMessages.slice(0, index)].reverse().find(item => item.role === 'user')
                      : undefined;
                    return (
                      <ChatMessage
                        key={msg.id}
                        message={msg}
                        onRefine={(prompt) => handleSubmit(undefined, prompt)}
                        onRegenerate={handleRegenerate}
                        onEditPrompt={handleEditPrompt}
                        onRetry={previousUser ? () => handleSubmit(undefined, previousUser.content) : undefined}
                        onFeedbackSubmit={handleFeedbackSubmit}
                      />
                    );
                  })}
                  {/* Streaming message realtime */}
                  {streamingMessage && (
                    <ChatMessage
                      key="streaming"
                      message={streamingMessage}
                      isStreaming={true}
                      onRefine={(prompt) => handleSubmit(undefined, prompt)}
                      onRegenerate={handleRegenerate}
                      onEditPrompt={handleEditPrompt}
                    />
                  )}
                </>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="absolute bottom-0 left-0 right-0 pt-8 sm:pt-10 pb-[max(0.75rem,env(safe-area-inset-bottom))] px-3 sm:px-4 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent dark:from-[#171717] dark:via-[#171717]">
          <div className={`${CHAT_ROW_WIDTH_CLASS} flex lg:gap-4`}>
            <div className="hidden lg:block h-8 w-8 shrink-0" aria-hidden="true" />
            <div className={`${CHAT_CONTENT_WIDTH_CLASS} relative min-w-0`}>
            {/* Scroll to bottom button */}
            {!isAtBottom && currentMessages.length > 0 && (
              <div className="absolute -top-13 sm:-top-14 left-1/2 -translate-x-1/2 z-20 fade-in slide-in-from-bottom-2 duration-200">
                <button
                  onClick={scrollToBottom}
                  className="w-10 h-10 bg-white dark:bg-[#1f1f1f] rounded-full flex items-center justify-center shadow-[0_2px_10px_rgba(0,0,0,0.12)] border border-gray-100 dark:border-white/10 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-all hover:shadow-[0_4px_14px_rgba(0,0,0,0.15)] active:scale-95"
                  title="Cuộn xuống"
                  aria-label="Cuộn xuống cuối cuộc trò chuyện"
                >
                  <ArrowDown className="w-5 h-5" />
                </button>
              </div>
            )}

            <div className="relative rounded-2xl sm:rounded-3xl bg-white dark:bg-[#1e1e1e] border border-gray-200/80 dark:border-white/10 shadow-xl shadow-blue-100/30 dark:shadow-none input-glow transition-all duration-300">
              <div className="flex items-center justify-between gap-2 px-2.5 sm:px-3 pt-2.5 sm:pt-3 pb-1 min-w-0">
                <div className="relative flex items-center min-w-0" ref={categoryRef}>
                  <button
                    type="button"
                    onClick={() => setIsCategoryOpen(!isCategoryOpen)}
                    className="flex w-fit max-w-full sm:max-w-[260px] md:max-w-[320px] items-center rounded-xl border border-gray-200/70 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-2.5 sm:px-3 py-1.5 transition-colors hover:bg-gray-100 dark:hover:bg-white/10 active:bg-gray-200 dark:active:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
                    aria-haspopup="listbox"
                    aria-expanded={isCategoryOpen}
                  >
                    <LibraryBig className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 mr-1.5 sm:mr-2 shrink-0" />
                    <span className="truncate text-[11.5px] sm:text-[12px] font-bold text-gray-700 dark:text-gray-300">{selectedLawCategory.label}</span>
                    <ChevronDown className={`w-3 h-3 text-gray-400 dark:text-gray-500 ml-1.5 shrink-0 transition-transform duration-200 ${isCategoryOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {isCategoryOpen && (
                    <div className="absolute bottom-full left-0 z-50 mb-2 w-[min(320px,calc(100vw-2rem))] max-h-[55dvh] overflow-y-auto custom-scrollbar animate-in rounded-2xl border border-gray-100 dark:border-white/10 bg-white dark:bg-[#1f1f1f] py-1 shadow-xl shadow-gray-200/50 dark:shadow-black/40 fade-in slide-in-from-bottom-2 duration-200" role="listbox">
                      <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 border-b border-gray-50 dark:border-white/10 mb-1 sticky top-0 bg-white dark:bg-[#1f1f1f]">Tra cứu theo lĩnh vực</div>
                      {LAW_CATEGORIES.map(category => (
                        <button
                          key={category.id}
                          onClick={() => { setLawCategory(category.id); setIsCategoryOpen(false); }}
                          className={`flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-[12.5px] sm:text-[12px] font-bold transition-colors ${lawCategory === category.id ? 'text-blue-700 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-500/10' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5'}`}
                          role="option"
                          aria-selected={lawCategory === category.id}
                        >
                          <span className="truncate">{category.label}</span>
                          {lawCategory === category.id && <Check className="h-4 w-4 flex-shrink-0 text-blue-600 dark:text-blue-400" />}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex shrink-0 items-center justify-end gap-2">
                  <ProviderSelector model={model} />
                </div>
              </div>

              <div className="flex items-end gap-2 px-3 sm:px-4 pt-1 pb-2.5 sm:pb-3">
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
                  placeholder={isLoading ? 'Đang xử lý yêu cầu...' : 'Hỏi về điều luật, thủ tục pháp lý...'}
                  className="flex-1 min-w-0 resize-none bg-transparent py-2 focus:outline-none overflow-y-hidden text-gray-700 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 leading-6 text-base sm:text-[15px] custom-scrollbar"
                  rows={1}
                  style={{ minHeight: '40px', maxHeight: '160px' }}
                />

                {/* Nut Send / Stop */}
                {isLoading ? (
                  <button
                    onClick={handleAbort}
                    title="Dừng tạo câu trả lời (Enter)"
                    aria-label="Dừng trả lời"
                    className="shrink-0 h-10 w-10 text-white rounded-xl sm:rounded-2xl transition-all shadow-md active:scale-95 flex items-center justify-center animate-pulse"
                    style={{ background: 'linear-gradient(135deg, #EF4444, #DC2626)' }}
                  >
                    <Square className="w-4 h-4 fill-white" />
                  </button>
                ) : (
                  <button
                    onClick={() => handleSubmit()}
                    disabled={!input.trim()}
                    aria-label="Gửi câu hỏi"
                    className={`shrink-0 h-10 w-10 text-white rounded-xl sm:rounded-2xl disabled:opacity-40 transition-all shadow-md active:scale-95 flex items-center justify-center ${input.trim() ? 'send-btn-ready' : ''}`}
                    style={{ background: 'linear-gradient(135deg, #2563EB, #1D4ED8)' }}
                  >
                    <Send className="w-4 h-4 translate-x-px translate-y-px" />
                  </button>
                )}
              </div>
            </div>
            <p className="text-center mt-2 text-[10px] leading-4 text-gray-400 dark:text-gray-500 font-medium px-2">
              AI có thể có sai sót. Hãy kiểm tra lại thông tin quan trọng.
            </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
