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

// Các nhóm văn bản dùng để giới hạn phạm vi truy xuất.
export const LAW_CATEGORIES = [
  {
    id: ALL_LAWS_CATEGORY,
    label: 'Tất cả văn bản',
    description: 'Tra cứu trên toàn bộ kho văn bản pháp luật',
  },
  {
    id: 'land',
    label: 'Đất đai',
    description: 'Quản lý, sử dụng và quyền đối với đất đai',
  },
  {
    id: 'housing-construction',
    label: 'Nhà ở & Xây dựng',
    description: 'Nhà ở, công trình và hoạt động xây dựng',
  },
  {
    id: 'real-estate-business',
    label: 'Kinh doanh bất động sản',
    description: 'Giao dịch, dự án và dịch vụ bất động sản',
  },
  {
    id: 'environment',
    label: 'Môi trường',
    description: 'Bảo vệ môi trường và quản lý tác động môi trường',
  },
  {
    id: 'notary',
    label: 'Công chứng',
    description: 'Tổ chức, hoạt động và thủ tục công chứng',
  },
  {
    id: 'civil-procedure',
    label: 'Tố tụng dân sự',
    description: 'Trình tự, thủ tục giải quyết vụ việc dân sự',
  },
  {
    id: 'criminal-mutual-assistance',
    label: 'Tương trợ tư pháp hình sự',
    description: 'Hợp tác và tương trợ tư pháp trong lĩnh vực hình sự',
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
