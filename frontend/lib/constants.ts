/**
 * Hằng số dùng chung cho toàn frontend.
 * Tách từ ChatInterface.tsx và ProviderSelector.tsx.
 */
import type { AIModel } from './types';

export interface LawCategory {
  id: string;
  label: string;
  description: string;
}

export const ALL_LAWS_CATEGORY = 'all';

// Các nhóm pháp luật dùng để giới hạn phạm vi truy xuất.
export const LAW_CATEGORIES = [
  {
    id: ALL_LAWS_CATEGORY,
    label: 'Tất cả các luật',
    description: 'Tra cứu trên toàn bộ kho dữ liệu pháp luật',
  },
  {
    id: 'civil-family-personal',
    label: 'Dân sự, Hôn nhân & Hộ tịch',
    description: 'Quan hệ dân sự, gia đình và quyền nhân thân',
  },
  {
    id: 'land-property-environment',
    label: 'Đất đai, Nhà ở & Xây dựng',
    description: 'Bất động sản, xây dựng, tài nguyên và môi trường',
  },
  {
    id: 'traffic-order-sanctions',
    label: 'Giao thông & Vi phạm hành chính',
    description: 'An toàn giao thông, trật tự và xử phạt',
  },
] as const satisfies readonly LawCategory[];

// Danh sách model AI hỗ trợ
export const AI_MODELS: AIModel[] = [
  { id: 'Qwen/Qwen3.5-9B', name: 'Qwen 3.5', fullName: 'Qwen3.5 9B' },
  { id: 'google/gemma-4-31B-it', name: 'Gemma 4', fullName: 'Gemma 4 31B' },
  { id: 'meta-llama/Llama-3.1-8B-Instruct', name: 'Llama 3.1', fullName: 'Llama 3.1 8B' },
  { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', name: 'DeepSeek R1', fullName: 'DeepSeek R1 7B' },
];

// Model mặc định
export const DEFAULT_MODEL = 'google/gemma-4-31B-it';

// LocalStorage keys
export const STORAGE_KEYS = {
  sessions: 'vietlaw_sessions',
  messages: 'vietlaw_messages',
} as const;
