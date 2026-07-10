import { DEFAULT_MODEL } from './constants';

export interface AISettings {
  model: string;
  temperature: number;
  maxTokens: number;
  topK: number;
  candidateK: number;
  cacheThreshold: number;
  maxSubqueries: number;
  historyMessages: number;
  enableQueryRewriter: boolean;
  enableReranker: boolean;
  enableSemanticCache: boolean;
  enableMemory: boolean;
}

export const AI_SETTINGS_STORAGE_KEY = 'vietlaw_ai_settings';
export const AI_SETTINGS_UPDATED_EVENT = 'vietlaw-ai-settings-updated';

export const DEFAULT_AI_SETTINGS: AISettings = {
  model: DEFAULT_MODEL,
  temperature: 0.3,
  maxTokens: 1024,
  topK: 5,
  candidateK: 60,
  cacheThreshold: 0.95,
  maxSubqueries: 3,
  historyMessages: 4,
  enableQueryRewriter: true,
  enableReranker: true,
  enableSemanticCache: true,
  enableMemory: true,
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export function normalizeAISettings(value: Partial<AISettings> | null | undefined): AISettings {
  return {
    model: typeof value?.model === 'string' && value.model ? value.model : DEFAULT_AI_SETTINGS.model,
    temperature: clamp(Number(value?.temperature ?? DEFAULT_AI_SETTINGS.temperature), 0, 1),
    maxTokens: Math.round(clamp(Number(value?.maxTokens ?? DEFAULT_AI_SETTINGS.maxTokens), 100, 4000)),
    topK: Math.round(clamp(Number(value?.topK ?? DEFAULT_AI_SETTINGS.topK), 1, 20)),
    candidateK: Math.round(clamp(Number(value?.candidateK ?? DEFAULT_AI_SETTINGS.candidateK), 10, 100)),
    cacheThreshold: clamp(Number(value?.cacheThreshold ?? DEFAULT_AI_SETTINGS.cacheThreshold), 0.8, 0.99),
    maxSubqueries: Math.round(clamp(Number(value?.maxSubqueries ?? DEFAULT_AI_SETTINGS.maxSubqueries), 1, 5)),
    historyMessages: Math.round(clamp(Number(value?.historyMessages ?? DEFAULT_AI_SETTINGS.historyMessages), 0, 10)),
    enableQueryRewriter: value?.enableQueryRewriter ?? DEFAULT_AI_SETTINGS.enableQueryRewriter,
    enableReranker: value?.enableReranker ?? DEFAULT_AI_SETTINGS.enableReranker,
    enableSemanticCache: value?.enableSemanticCache ?? DEFAULT_AI_SETTINGS.enableSemanticCache,
    enableMemory: value?.enableMemory ?? DEFAULT_AI_SETTINGS.enableMemory,
  };
}

export function readAISettings(): AISettings {
  if (typeof window === 'undefined') return DEFAULT_AI_SETTINGS;

  try {
    const raw = window.localStorage.getItem(AI_SETTINGS_STORAGE_KEY);
    return raw ? normalizeAISettings(JSON.parse(raw)) : DEFAULT_AI_SETTINGS;
  } catch {
    return DEFAULT_AI_SETTINGS;
  }
}

export function persistAISettings(settings: AISettings): AISettings {
  const normalized = normalizeAISettings(settings);
  window.localStorage.setItem(AI_SETTINGS_STORAGE_KEY, JSON.stringify(normalized));
  window.dispatchEvent(new CustomEvent(AI_SETTINGS_UPDATED_EVENT, { detail: normalized }));
  return normalized;
}
