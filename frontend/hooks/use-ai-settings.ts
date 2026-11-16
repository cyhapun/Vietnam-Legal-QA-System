'use client';

import { useState } from 'react';
import {
  AISettings,
  DEFAULT_AI_SETTINGS,
} from '@/lib/ai-settings';

export function useAISettings() {
  const [settings] = useState<AISettings>(DEFAULT_AI_SETTINGS);
  return { settings, isLoaded: true };
}
