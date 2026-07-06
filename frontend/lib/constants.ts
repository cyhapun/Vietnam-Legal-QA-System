/**
 * Hằng số dùng chung cho toàn frontend.
 * Tách từ ChatInterface.tsx và ProviderSelector.tsx.
 */
import type { AIModel } from './types';

export interface LawCategory {
  id: string;
  label: string;
}

export const ALL_LAWS_CATEGORY = 'all';

// Các lĩnh vực pháp luật được tách từ ba nhóm nghiệp vụ.
export const LAW_CATEGORIES = [
  {
    id: ALL_LAWS_CATEGORY,
    label: 'Tất cả các luật',
  },
  {
    id: 'civil',
    label: 'Dân sự',
  },
  {
    id: 'family-personal',
    label: 'Gia đình & Nhân thân',
  },
  {
    id: 'land',
    label: 'Đất đai',
  },
  {
    id: 'real-estate',
    label: 'Bất động sản',
  },
  {
    id: 'construction-environment',
    label: 'Xây dựng & Môi trường',
  },
  {
    id: 'traffic',
    label: 'Giao thông',
  },
  {
    id: 'public-order-sanctions',
    label: 'Trật tự & Xử phạt',
  },
] as const satisfies readonly LawCategory[];

// Danh sách model AI hỗ trợ
export const AI_MODELS: AIModel[] = [
  { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen 2.5', fullName: 'Qwen2.5 7B' },
  { id: 'google/gemma-4-31B-it', name: 'Gemma 4', fullName: 'Gemma 4 31B' },
  { id: 'meta-llama/Llama-3.1-8B-Instruct', name: 'Llama 3.1', fullName: 'Llama 3.1 8B' },
  { id: 'deepseek-ai/DeepSeek-R1-Distill-Llama-8B', name: 'DeepSeek R1', fullName: 'DeepSeek R1 8B' },
];

// Model mặc định
export const DEFAULT_MODEL = 'deepseek-ai/DeepSeek-R1-Distill-Llama-8B';

// LocalStorage keys
export const STORAGE_KEYS = {
  sessions: 'vietlaw_sessions',
  messages: 'vietlaw_messages',
} as const;
