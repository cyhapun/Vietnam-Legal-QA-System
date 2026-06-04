/**
 * Shared TypeScript interfaces cho toàn bộ frontend.
 * Tách từ các component để tránh circular imports và dễ tái sử dụng.
 */

// --- Chat Message ---
export interface DocumentChunk {
  content: string;
  metadata: {
    source?: string;
    dieu?: string;
    khoan?: string;
    diem?: string;
    law?: string;
  };
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  contextUsed?: DocumentChunk[];
}

// --- Chat Session ---
export interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: number;
}

// --- Model ---
export interface AIModel {
  id: string;
  name: string;
  fullName: string;
}

// --- API ---
export interface ChatApiRequest {
  messages: { role: string; content: string }[];
  model: string;
  category: string;
}

export interface ChatApiResponse {
  text: string;
  contextUsed: DocumentChunk[];
}
