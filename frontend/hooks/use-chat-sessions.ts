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
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [isSessionsListLoading, setIsSessionsListLoading] = useState(true);
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
  const handleSelectSession = useCallback(async (id: string) => {
    const { currentSessionId, messagesBySession } = stateRef.current;
    if (id === currentSessionId) return;

    // Khi chuyển sang session khác, lọc bỏ các session rỗng cũ
    setSessions(prev => prev.filter(s => s.id === id || (messagesBySession[s.id] && messagesBySession[s.id].length > 0)));
    setCurrentSessionId(id);

    // Lazy load messages nếu chưa có
    if (!messagesBySession[id]) {
      setIsSessionLoading(true);
      try {
        const res = await fetch(`/api/chat/session/${id}/messages`);
        if (res.ok) {
          const dbMsgs: any[] = await res.json();
          const messages: Message[] = dbMsgs.map(m => ({
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            contextUsed: m.contextUsed || []
          }));
          setMessagesBySession(prev => ({ ...prev, [id]: messages }));
        } else {
          setMessagesBySession(prev => ({ ...prev, [id]: [] }));
        }
      } catch (err) {
        console.error('Lỗi khi fetch messages cho session:', id, err);
        setMessagesBySession(prev => ({ ...prev, [id]: [] }));
      } finally {
        setIsSessionLoading(false);
      }
    }
  }, []);

  // --- Xóa session ---
  const handleDeleteSession = useCallback((id: string) => {
    // Gọi API xóa ở backend không đồng bộ
    fetch(`/api/chat/session/${id}`, { method: 'DELETE' })
      .then(res => {
        if (!res.ok) console.warn(`[Delete Session] Backend trả về ${res.status} cho session ${id}`);
      })
      .catch(err => {
        console.error('Lỗi khi xóa session ở backend:', err);
      });

    // Cập nhật đồng thời cả sessions và messages trong cùng một lần render
    const { currentSessionId, sessions, messagesBySession } = stateRef.current;
    const remaining = sessions.filter(s => s.id !== id);

    // Xóa messages của session bị xóa
    const nextMessages = { ...messagesBySession };
    delete nextMessages[id];
    setMessagesBySession(nextMessages);

    if (currentSessionId === id) {
      if (remaining.length > 0) {
        setCurrentSessionId(remaining[0].id);
        setSessions(remaining);
      } else {
        // Tạo session mới nếu không còn session nào
        const newId = Date.now().toString();
        const newSession: ChatSession = {
          id: newId,
          title: 'Cuộc trò chuyện mới',
          lastMessage: '',
          timestamp: Date.now(),
        };
        nextMessages[newId] = [];
        setMessagesBySession({ ...nextMessages });
        setCurrentSessionId(newId);
        setSessions([newSession]);
      }
    } else {
      setSessions(remaining);
    }
  }, []);

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

  // --- Load từ DB/API khi mount ---
  useEffect(() => {
    setIsMounted(true);

    const loadFromDB = async () => {
      try {
        const res = await fetch('/api/chat/sessions');
        if (!res.ok) throw new Error('Failed to fetch sessions');
        const dbSessions: any[] = await res.json();

        const filteredSessions = dbSessions.filter(s => s.message_count > 0);

        const loadedSessions: ChatSession[] = filteredSessions.map(dbSession => ({
          id: dbSession.session_id,
          title: dbSession.title || 'Cuộc trò chuyện mới',
          lastMessage: '',
          timestamp: dbSession.updated_at ? new Date(dbSession.updated_at).getTime() : Date.now(),
        }));

        loadedSessions.sort((a, b) => b.timestamp - a.timestamp);

        // Khởi tạo một session mới thay vì fetch messages của session cũ
        const newId = Date.now().toString();
        const newSession: ChatSession = {
          id: newId,
          title: 'Cuộc trò chuyện mới',
          lastMessage: '',
          timestamp: Date.now(),
        };

        loadedSessions.unshift(newSession);

        setSessions(loadedSessions);
        setMessagesBySession({ [newId]: [] });
        setCurrentSessionId(newId);
        setIsSessionLoading(false);
      } catch (err) {
        console.error('Lỗi khi load DB sessions, fallback to localStorage:', err);
        // Fallback to localStorage
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
      } finally {
        setIsSessionsListLoading(false);
      }
    };

    loadFromDB();
  }, [handleNewChat]);

  // --- Lưu vào localStorage khi thay đổi ---
  useEffect(() => {
    if (isMounted) {
      const validSessions = sessions.filter(s => messagesBySession[s.id] && messagesBySession[s.id].length > 0);
      // Chỉ lưu messages của các session hợp lệ để tránh tích lũy orphan data
      const validMessages: Record<string, Message[]> = {};
      validSessions.forEach(s => { validMessages[s.id] = messagesBySession[s.id]; });
      localStorage.setItem(STORAGE_KEYS.sessions, JSON.stringify(validSessions));
      localStorage.setItem(STORAGE_KEYS.messages, JSON.stringify(validMessages));
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
    isSessionLoading,
    isSessionsListLoading,
  };
}
