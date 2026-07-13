/**
 * Hook quản lý toàn bộ logic chat sessions.
 * Tách từ ChatInterface.tsx để component chỉ lo render UI.
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import type { ChatSession, Message } from '@/lib/types';
import { STORAGE_KEYS } from '@/lib/constants';

const createSessionId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

const mapDbMessage = (m: any): Message => ({
  id: m.id,
  role: m.role as 'user' | 'assistant',
  content: m.content,
  contextUsed: m.contextUsed || []
});

const chooseCompleteMessages = (cached: Message[] | undefined, dbMessages: Message[]) => {
  if (!cached || dbMessages.length >= cached.length) {
    return dbMessages;
  }
  return cached;
};

export function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [isSessionsListLoading, setIsSessionsListLoading] = useState(true);
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({});
  const [isMounted, setIsMounted] = useState(false);
  const sessionLoadSeqRef = useRef(0);

  const stateRef = useRef({ sessions, currentSessionId, messagesBySession });
  useEffect(() => {
    stateRef.current = { sessions, currentSessionId, messagesBySession };
  }, [sessions, currentSessionId, messagesBySession]);

  const currentMessages = currentSessionId
    ? messagesBySession[currentSessionId] || []
    : [];

  // --- Tạo session mới ---
  const handleNewChat = useCallback(() => {
    const { currentSessionId, messagesBySession } = stateRef.current;
    
    // Nếu đang ở session rỗng rồi thì không tạo thêm
    if (currentSessionId && (!messagesBySession[currentSessionId] || messagesBySession[currentSessionId].length === 0)) {
      return;
    }

    const newId = createSessionId();
    setCurrentSessionId(newId);
    localStorage.setItem(STORAGE_KEYS.activeSessionId, newId);
    setMessagesBySession(prev => ({ ...prev, [newId]: [] }));
  }, []);

  // --- Chọn session ---
  const handleSelectSession = useCallback(async (id: string) => {
    const { currentSessionId, messagesBySession } = stateRef.current;
    if (id === currentSessionId) return;

    const loadSeq = ++sessionLoadSeqRef.current;
    setCurrentSessionId(id);
    localStorage.setItem(STORAGE_KEYS.activeSessionId, id);

    const cachedMessages = messagesBySession[id];
    if (!cachedMessages) {
      setIsSessionLoading(true);
    }

    try {
      const res = await fetch(`/api/chat/session/${id}/messages`);
      if (res.ok) {
        const dbMsgs: any[] = await res.json();
        const dbMessages = dbMsgs.map(mapDbMessage);
        setMessagesBySession(prev => ({
          ...prev,
          [id]: chooseCompleteMessages(prev[id], dbMessages)
        }));
      } else if (!cachedMessages) {
        setMessagesBySession(prev => ({ ...prev, [id]: [] }));
      }
    } catch (err) {
      console.error('Error fetching messages for session:', id, err);
      if (!cachedMessages) {
        setMessagesBySession(prev => ({ ...prev, [id]: [] }));
      }
    } finally {
      if (sessionLoadSeqRef.current === loadSeq) {
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
        localStorage.setItem(STORAGE_KEYS.activeSessionId, remaining[0].id);
        setSessions(remaining);
      } else {
        // Tạo ID mới nếu không còn session nào, nhưng KHÔNG add vào sessions list
        const newId = createSessionId();
        nextMessages[newId] = [];
        setMessagesBySession({ ...nextMessages });
        setCurrentSessionId(newId);
        localStorage.setItem(STORAGE_KEYS.activeSessionId, newId);
        setSessions([]);
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

    setSessions(prev => {
      const idx = prev.findIndex(s => s.id === currentSessionId);
      if (idx === -1) {
        return [{
          id: currentSessionId,
          title: message.content.substring(0, 40) + (message.content.length > 40 ? '...' : ''),
          lastMessage: message.content,
          timestamp: Date.now()
        }, ...prev];
      }
      return prev.map(s =>
        s.id === currentSessionId
          ? { ...s, lastMessage: message.content, timestamp: Date.now() }
          : s
      );
    });
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
        const savedActiveSessionId = localStorage.getItem(STORAGE_KEYS.activeSessionId);
        const savedSessionsRaw = localStorage.getItem(STORAGE_KEYS.sessions);
        const savedMessagesRaw = localStorage.getItem(STORAGE_KEYS.messages);
        const savedSessions: ChatSession[] = savedSessionsRaw ? JSON.parse(savedSessionsRaw) : [];
        const savedMessages: Record<string, Message[]> = savedMessagesRaw ? JSON.parse(savedMessagesRaw) : {};

        const filteredSessions = dbSessions.filter(s => s.message_count > 0);
        const dbMessageCounts = Object.fromEntries(
          filteredSessions.map(s => [s.session_id, Number(s.message_count || 0)])
        ) as Record<string, number>;

        let loadedSessions: ChatSession[] = filteredSessions.map(dbSession => ({
          id: dbSession.session_id,
          title: dbSession.title || 'Cuộc trò chuyện mới',
          lastMessage: '',
          timestamp: dbSession.updated_at ? new Date(dbSession.updated_at).getTime() : Date.now(),
        }));

        loadedSessions.sort((a, b) => b.timestamp - a.timestamp);

        // Restore the active conversation first; create a blank one only when none exists.
        if (
          savedActiveSessionId &&
          !loadedSessions.some(s => s.id === savedActiveSessionId) &&
          savedMessages[savedActiveSessionId]?.length > 0
        ) {
          const localSession = savedSessions.find(s => s.id === savedActiveSessionId);
          const firstMessage = savedMessages[savedActiveSessionId].find(m => m.role === 'user');
          loadedSessions = [
            localSession || {
              id: savedActiveSessionId,
              title: firstMessage
                ? firstMessage.content.substring(0, 30) + (firstMessage.content.length > 30 ? '...' : '')
                : 'Cuoc tro chuyen moi',
              lastMessage: savedMessages[savedActiveSessionId].at(-1)?.content || '',
              timestamp: Date.now()
            },
            ...loadedSessions,
          ];
        }

        const shouldRestoreActive = Boolean(
          savedActiveSessionId && loadedSessions.some(s => s.id === savedActiveSessionId)
        );
        const activeId = shouldRestoreActive && savedActiveSessionId
          ? savedActiveSessionId
          : createSessionId();
        const initialMessages: Record<string, Message[]> = savedMessages[activeId]
          ? { [activeId]: savedMessages[activeId] }
          : { [activeId]: [] };

        setSessions(loadedSessions);
        setMessagesBySession(initialMessages);
        setCurrentSessionId(activeId);
        localStorage.setItem(STORAGE_KEYS.activeSessionId, activeId);

        const cachedActiveMessages = savedMessages[activeId];
        const shouldFetchActiveMessages =
          shouldRestoreActive &&
          (!cachedActiveMessages || (dbMessageCounts[activeId] || 0) > cachedActiveMessages.length);

        if (shouldFetchActiveMessages) {
          setIsSessionLoading(true);
          const messagesRes = await fetch(`/api/chat/session/${activeId}/messages`);
          if (messagesRes.ok) {
            const dbMsgs: any[] = await messagesRes.json();
            const dbMessages = dbMsgs.map(mapDbMessage);
            setMessagesBySession(prev => ({
              ...prev,
              [activeId]: chooseCompleteMessages(prev[activeId], dbMessages)
            }));
          }
        }
        setIsSessionLoading(false);
      } catch (err) {
        console.error('Lỗi khi load DB sessions, fallback to localStorage:', err);
        // Fallback to localStorage
        const savedSessions = localStorage.getItem(STORAGE_KEYS.sessions);
        const savedMessages = localStorage.getItem(STORAGE_KEYS.messages);
        const savedActiveSessionId = localStorage.getItem(STORAGE_KEYS.activeSessionId);
        if (savedSessions && savedMessages) {
          const parsedSessions = JSON.parse(savedSessions);
          const parsedMessages = JSON.parse(savedMessages);
          setSessions(parsedSessions);
          setMessagesBySession(parsedMessages);
          if (savedActiveSessionId && parsedMessages[savedActiveSessionId]) {
            setCurrentSessionId(savedActiveSessionId);
          } else if (parsedSessions.length > 0) {
            setCurrentSessionId(parsedSessions[0].id);
            localStorage.setItem(STORAGE_KEYS.activeSessionId, parsedSessions[0].id);
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
      if (currentSessionId) {
        localStorage.setItem(STORAGE_KEYS.activeSessionId, currentSessionId);
      }
    }
  }, [sessions, messagesBySession, currentSessionId, isMounted]);

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
