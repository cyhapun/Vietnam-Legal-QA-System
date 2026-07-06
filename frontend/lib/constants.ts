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
    id: 'LKDBDS_2023',
    label: 'Luật Kinh doanh bất động sản 2023',
  },
  {
    id: 'LTTPHS_2025',
    label: 'Luật Tương trợ tư pháp về hình sự 2025',
  },
  {
    id: 'LNO_2023',
    label: 'Luật Nhà ở 2023',
  },
  {
    id: 'LBVMT_2020',
    label: 'Luật Bảo vệ môi trường 2020',
  },
  {
    id: 'LXD_2014',
    label: 'Luật Xây dựng 2014',
  },
  {
    id: 'LDD_2024',
    label: 'Luật Đất đai 2024',
  },
  {
    id: 'LCC_2024',
    label: 'Luật Công chứng 2024',
  },
  {
    id: 'BLTTDS_2015',
    label: 'Bộ luật Tố tụng dân sự 2015',
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
