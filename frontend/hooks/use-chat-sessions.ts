/**
 * Hook quản lý toàn bộ logic chat sessions.
 * Tách từ ChatInterface.tsx để component chỉ lo render UI.
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import type { ChatSession, Message } from '@/lib/types';
import { STORAGE_KEYS } from '@/lib/constants';

export function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({});
  const [isMounted, setIsMounted] = useState(false);

  const currentMessages = currentSessionId
    ? messagesBySession[currentSessionId] || []
    : [];

  // --- Tạo session mới ---
  const handleNewChat = useCallback(() => {
    const newId = Date.now().toString();
    const newSession: ChatSession = {
      id: newId,
      title: 'Cuộc trò chuyện mới',
      lastMessage: '',
      timestamp: Date.now(),
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newId);
    setMessagesBySession(prev => ({ ...prev, [newId]: [] }));
  }, []);

  // --- Chọn session ---
  const handleSelectSession = useCallback((id: string) => {
    setCurrentSessionId(id);
  }, []);

  // --- Xóa session ---
  const handleDeleteSession = useCallback((id: string) => {
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
      localStorage.setItem(STORAGE_KEYS.sessions, JSON.stringify(sessions));
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
    updateSessionTitle,
  };
}
