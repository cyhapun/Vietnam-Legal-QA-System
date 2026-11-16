import { DEFAULT_MODEL } from './constants';

export interface AISettings {
  model: string;
}

export const DEFAULT_AI_SETTINGS: AISettings = {
  model: DEFAULT_MODEL,
};

export function readAISettings(): AISettings {
  return DEFAULT_AI_SETTINGS;
}

export function persistAISettings(settings: AISettings): AISettings {
  return settings;
}

export function normalizeAISettings(settings?: Partial<AISettings> | null): AISettings {
  return {
    model: settings?.model || DEFAULT_MODEL,
  };
}
