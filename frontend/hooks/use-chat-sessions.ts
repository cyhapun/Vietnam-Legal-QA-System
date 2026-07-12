/**
 * Hook quản lý toàn bộ logic chat sessions.
 * Tách từ ChatInterface.tsx để component chỉ lo render UI.
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import type { ChatSession, Message } from '@/lib/types';
import { STORAGE_KEYS } from '@/lib/constants';

export function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({});
  const [isMounted, setIsMounted] = useState(false);

  const stateRef = useRef({ sessions, currentSessionId, messagesBySession });
  useEffect(() => {
    stateRef.current = { sessions, currentSessionId, messagesBySession };
  }, [sessions, currentSessionId, messagesBySession]);

  const currentMessages = currentSessionId
    ? messagesBySession[currentSessionId] || []
    : [];

  // --- Tạo session mới ---
  const handleNewChat = useCallback(() => {
    const { currentSessionId, messagesBySession, sessions } = stateRef.current;
    
    // Nếu đang ở session rỗng rồi thì không tạo thêm
    if (currentSessionId && (!messagesBySession[currentSessionId] || messagesBySession[currentSessionId].length === 0)) {
      return;
    }

    const newId = Date.now().toString();
    const newSession: ChatSession = {
      id: newId,
      title: 'Cuộc trò chuyện mới',
      lastMessage: '',
      timestamp: Date.now(),
    };

    // Lọc bỏ các session rỗng cũ
    const validSessions = sessions.filter(s => messagesBySession[s.id] && messagesBySession[s.id].length > 0);

    setSessions([newSession, ...validSessions]);
    setCurrentSessionId(newId);
    setMessagesBySession(prev => ({ ...prev, [newId]: [] }));
  }, []);

  // --- Chọn session ---
  const handleSelectSession = useCallback((id: string) => {
    const { currentSessionId, messagesBySession } = stateRef.current;
    if (id === currentSessionId) return;

    // Khi chuyển sang session khác, lọc bỏ các session rỗng cũ
    setSessions(prev => prev.filter(s => s.id === id || (messagesBySession[s.id] && messagesBySession[s.id].length > 0)));
    setCurrentSessionId(id);
  }, []);

  // --- Xóa session ---
  const handleDeleteSession = useCallback((id: string) => {
    // Gọi API xóa ở backend không đồng bộ
    fetch(`/api/chat/session/${id}`, { method: 'DELETE' }).catch(err => {
      console.error('Lỗi khi xóa session ở backend:', err);
    });

    const { currentSessionId } = stateRef.current;
    setSessions(prev => {
      const remaining = prev.filter(s => s.id !== id);
      // Nếu đang xóa session hiện tại, chuyển sang session khác
      if (currentSessionId === id) {
        if (remaining.length > 0) {
          setCurrentSessionId(remaining[0].id);
        } else {
          // Tạo session mới nếu không còn
          const newId = Date.now().toString();
          const newSession: ChatSession = {
            id: newId,
            title: 'Cuộc trò chuyện mới',
            lastMessage: '',
            timestamp: Date.now(),
          };
          setCurrentSessionId(newId);
          setMessagesBySession(prev => ({ ...prev, [newId]: [] }));
          return [newSession];
        }
      }
      return remaining;
    });

    setMessagesBySession(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, [currentSessionId]);

  // --- Thêm message vào session hiện tại ---
  const addMessage = useCallback((message: Message) => {
    if (!currentSessionId) return;
    setMessagesBySession(prev => ({
      ...prev,
      [currentSessionId]: [...(prev[currentSessionId] || []), message],
    }));
  }, [currentSessionId]);

  // --- Cập nhật message ---
  const updateMessage = useCallback((sessionId: string, messageId: string, updates: Partial<Message>) => {
    setMessagesBySession(prev => {
      const sessionMessages = prev[sessionId];
      if (!sessionMessages) return prev;
      return {
        ...prev,
        [sessionId]: sessionMessages.map(m => m.id === messageId ? { ...m, ...updates } : m)
      };
    });
  }, []);

  // --- Cập nhật title session ---
  const updateSessionTitle = useCallback((title: string) => {
    if (!currentSessionId) return;
    setSessions(prev =>
      prev.map(s =>
        s.id === currentSessionId
          ? { ...s, title: title.substring(0, 30) + (title.length > 30 ? '...' : '') }
          : s
      )
    );
  }, [currentSessionId]);

  // --- Load từ localStorage khi mount ---
  useEffect(() => {
    setIsMounted(true);
    const savedSessions = localStorage.getItem(STORAGE_KEYS.sessions);
    const savedMessages = localStorage.getItem(STORAGE_KEYS.messages);

    if (savedSessions && savedMessages) {
      const parsedSessions = JSON.parse(savedSessions);
      setSessions(parsedSessions);
      setMessagesBySession(JSON.parse(savedMessages));
      if (parsedSessions.length > 0) {
        setCurrentSessionId(parsedSessions[0].id);
      } else {
        handleNewChat();
      }
    } else {
      handleNewChat();
    }
  }, [handleNewChat]);

  // --- Lưu vào localStorage khi thay đổi ---
  useEffect(() => {
    if (isMounted) {
      const validSessions = sessions.filter(s => messagesBySession[s.id] && messagesBySession[s.id].length > 0);
      localStorage.setItem(STORAGE_KEYS.sessions, JSON.stringify(validSessions));
      localStorage.setItem(STORAGE_KEYS.messages, JSON.stringify(messagesBySession));
    }
  }, [sessions, messagesBySession, isMounted]);

  return {
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
  };
}
