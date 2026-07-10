import { DEFAULT_MODEL } from './constants';

export interface AISettings {
  model: string;
  temperature: number;
  maxTokens: number;
  topK: number;
}

export const AI_SETTINGS_STORAGE_KEY = 'vietlaw_ai_settings';
export const AI_SETTINGS_UPDATED_EVENT = 'vietlaw-ai-settings-updated';

export const DEFAULT_AI_SETTINGS: AISettings = {
  model: DEFAULT_MODEL,
  temperature: 0.3,
  maxTokens: 1024,
  topK: 5,
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export function normalizeAISettings(value: Partial<AISettings> | null | undefined): AISettings {
  return {
    model: typeof value?.model === 'string' && value.model ? value.model : DEFAULT_AI_SETTINGS.model,
    temperature: clamp(Number(value?.temperature ?? DEFAULT_AI_SETTINGS.temperature), 0, 1),
    maxTokens: Math.round(clamp(Number(value?.maxTokens ?? DEFAULT_AI_SETTINGS.maxTokens), 100, 4000)),
    topK: Math.round(clamp(Number(value?.topK ?? DEFAULT_AI_SETTINGS.topK), 1, 20)),
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
