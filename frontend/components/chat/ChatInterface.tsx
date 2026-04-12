'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Scale, PanelLeft, LibraryBig } from 'lucide-react'; 
import { ProviderSelector } from './ProviderSelector';
import { ChatMessage, Message } from './ChatMessage';
import { Sidebar, ChatSession } from './Sidebar';

export function ChatInterface() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({});
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [model, setModel] = useState('google/gemma-4-31B-it');
  
  // New State for Law Category filtering
  const [lawCategory, setLawCategory] = useState('Chung');
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMounted, setIsMounted] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const categories = [
    "Chung", "Kinh doanh", "Đất đai", "Bảo vệ môi trường", "Tố tụng dân sự", "Nhà ở"
  ];

  const currentMessages = currentSessionId ? messagesBySession[currentSessionId] || [] : [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages, isLoading]);

  useEffect(() => {
    setIsMounted(true);
    const savedSessions = localStorage.getItem('vietlaw_sessions');
    const savedMessages = localStorage.getItem('vietlaw_messages');

    if (savedSessions && savedMessages) {
      const parsedSessions = JSON.parse(savedSessions);
      setSessions(parsedSessions);
      setMessagesBySession(JSON.parse(savedMessages));
      if (parsedSessions.length > 0) setCurrentSessionId(parsedSessions[0].id);
      else handleNewChat();
    } else {
      handleNewChat();
    }
  }, []);

  useEffect(() => {
    if (isMounted) {
      localStorage.setItem('vietlaw_sessions', JSON.stringify(sessions));
      localStorage.setItem('vietlaw_messages', JSON.stringify(messagesBySession));
    }
  }, [sessions, messagesBySession, isMounted]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleNewChat = () => {
    const newId = Date.now().toString();
    const newSession: ChatSession = { id: newId, title: 'Cuộc trò chuyện mới', lastMessage: '', timestamp: Date.now() };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newId);
    setMessagesBySession(prev => ({ ...prev, [newId]: [] }));
  };

  const handleSelectSession = (id: string) => setCurrentSessionId(id);
  const handleDeleteSession = (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    setMessagesBySession(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    if (currentSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id);
      if (remaining.length > 0) setCurrentSessionId(remaining[0].id);
      else handleNewChat();
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading || !currentSessionId) return;

    const userText = input.trim();
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = '52px';

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: userText };

    setMessagesBySession(prev => ({
      ...prev, [currentSessionId]: [...(prev[currentSessionId] || []), userMessage]
    }));

    if (currentMessages.length === 0) {
      setSessions(prev => prev.map(s => 
        s.id === currentSessionId ? { ...s, title: userText.substring(0, 30) + (userText.length > 30 ? '...' : '') } : s
      ));
    }

    setIsLoading(true);

    try {
      const apiMessages = [...currentMessages, userMessage].map(m => ({ role: m.role, content: m.content }));
      
      // Đã thêm trường `category` vào Body request
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages, model: model, category: lawCategory }),
      });

      if (!response.ok) throw new Error('Failed to fetch response');
      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.text,
        contextUsed: data.contextUsed
      };

      setMessagesBySession(prev => ({
        ...prev, [currentSessionId]: [...(prev[currentSessionId] || []), assistantMessage]
      }));
    } catch (error) {
      setMessagesBySession(prev => ({
        ...prev, [currentSessionId]: [...(prev[currentSessionId] || []), {
          id: (Date.now() + 1).toString(), role: 'assistant',
          content: '⚠️ Xin lỗi, đã có lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại Backend.'
        }]
      }));
    } finally {
      setIsLoading(false);
    }
  };

  if (!isMounted) {
    return <div className="h-screen bg-[#F9FAFB] flex items-center justify-center">
      <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
    </div>;
  }

  return (
    <div className="flex h-screen bg-[#F9FAFB] overflow-hidden font-sans relative">
      <div className={`flex-shrink-0 transition-all duration-300 ease-in-out overflow-hidden h-full z-20 ${isSidebarOpen ? 'w-64 opacity-100' : 'w-0 opacity-0'}`}>
        <div className="w-64 h-full">
          <Sidebar sessions={sessions} currentSessionId={currentSessionId} onNewChat={handleNewChat} onSelectSession={handleSelectSession} onDeleteSession={handleDeleteSession} onCloseSidebar={() => setIsSidebarOpen(false)} />
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 relative h-full">
        <div className="flex items-center justify-between bg-white shadow-sm z-10 relative border-b border-gray-100 min-h-[64px] px-4">
          <div className="flex items-center gap-4">
            <div className={`transition-all duration-300 overflow-hidden flex items-center ${isSidebarOpen ? 'w-0 opacity-0' : 'w-8 opacity-100'}`}>
               <button onClick={() => setIsSidebarOpen(true)} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 hover:text-gray-800 transition-colors" title="Mở sidebar">
                  <PanelLeft className="w-5 h-5" />
               </button>
            </div>
            
            {/* Category Selector UI */}
            <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5">
              <LibraryBig className="w-4 h-4 text-gray-500" />
              <select 
                value={lawCategory} 
                onChange={(e) => setLawCategory(e.target.value)}
                className="bg-transparent text-sm font-medium text-gray-700 focus:outline-none cursor-pointer"
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat === "Chung" ? "Tất cả lĩnh vực" : `Luật ${cat}`}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex-1 max-w-[200px] ml-auto">
            <ProviderSelector model={model} setModel={setModel}/>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto scroll-smooth">
          {currentMessages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-4 animate-in fade-in duration-500">
              <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mb-6 shadow-sm">
                <Scale className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">VietLaw AI Assistant</h2>
              <p className="text-gray-500 max-w-md">
                Đang tra cứu: <strong className="text-blue-600">{lawCategory === "Chung" ? "Tất cả lĩnh vực" : `Lĩnh vực ${lawCategory}`}</strong>
              </p>
            </div>
          ) : (
            <div className="pb-8">
              {currentMessages.map(msg => <ChatMessage key={msg.id} message={msg} />)}
              {isLoading && (
                <div className="py-6 bg-transparent">
                  <div className="max-w-4xl mx-auto px-4 flex space-x-4">
                    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm">
                      <Loader2 className="w-4 h-4 text-white animate-spin" />
                    </div>
                    <div className="flex items-center">
                      <div className="flex space-x-1.5 items-center bg-white px-4 py-2.5 rounded-2xl border border-gray-100 shadow-sm">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="bg-gradient-to-t from-[#F9FAFB] via-[#F9FAFB] to-transparent pt-6 pb-4 px-4 border-t border-gray-100">
          <div className="max-w-4xl mx-auto relative">
            <div className="relative shadow-sm rounded-2xl bg-white border border-gray-200 focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-50 transition-all">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInput}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
                }}
                placeholder="Hỏi về bất kỳ vấn đề pháp lý nào... (Shift + Enter để xuống dòng)"
                className="w-full resize-none bg-transparent pl-4 pr-14 py-3.5 focus:outline-none text-gray-700 leading-relaxed custom-scrollbar"
                rows={1}
                style={{ minHeight: '52px', maxHeight: '200px' }}
              />
              <button
                onClick={(e) => handleSubmit(e as any)}
                disabled={!input.trim() || isLoading}
                className="absolute right-2 bottom-2 p-2 text-white bg-blue-600 rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600 transition-all shadow-sm"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}