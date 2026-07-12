import React, { useState } from 'react';
import { KeyRound, Save, ShieldCheck, Trash2 } from 'lucide-react';
import { AI_MODELS, AI_PROVIDERS } from '@/lib/constants';
import {
  AISettings,
  isInferenceConfigured,
  setRoleByModel,
} from '@/lib/ai-settings';
import type { InferenceProviderId, InferenceRoleId } from '@/lib/types';

interface InferenceSetupModalProps {
  settings: AISettings;
  setSettings: (settings: AISettings | ((current: AISettings) => AISettings)) => void;
}

const ROLE_LABELS: Record<InferenceRoleId, string> = {
  answer: 'Answer LLM',
  rewriter: 'Query Rewriter',
  summarizer: 'Memory Summarizer',
};

export function InferenceSetupModal({ settings, setSettings }: InferenceSetupModalProps) {
  const [draft, setDraft] = useState(settings);
  const ready = isInferenceConfigured(draft);

  const updateCredential = (provider: InferenceProviderId, apiKey: string) => {
    setDraft(current => ({
      ...current,
      providerCredentials: {
        ...current.providerCredentials,
        [provider]: {
          apiKey,
          remember: current.providerCredentials[provider]?.remember ?? true,
        },
      },
    }));
  };

  const updateRemember = (provider: InferenceProviderId, remember: boolean) => {
    setDraft(current => ({
      ...current,
      providerCredentials: {
        ...current.providerCredentials,
        [provider]: {
          apiKey: current.providerCredentials[provider]?.apiKey ?? '',
          remember,
        },
      },
    }));
  };

  const updateRole = (role: InferenceRoleId, modelId: string) => {
    setDraft(current => setRoleByModel(current, role, modelId));
  };

  const save = () => {
    if (!ready) return;
    setSettings(draft);
  };

  const clear = () => {
    setDraft(current => ({
      ...current,
      providerCredentials: {
        google: { apiKey: '', remember: true },
        huggingface: { apiKey: '', remember: true },
      },
    }));
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 px-4 backdrop-blur-sm">
      <div className="w-full max-w-3xl rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-5 flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-950 dark:text-white">Set up inference providers</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
              Configure a supported remote provider before asking legal questions. API keys stay in this browser and are sent to the backend only for inference requests.
            </p>
          </div>
        </div>

        <div className="mb-4 rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-xs leading-5 text-emerald-800 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300">
          <ShieldCheck className="mr-2 inline h-4 w-4" />
          Retrieval embeddings are server-managed and fixed to HuggingFace BAAI/bge-m3.
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {AI_PROVIDERS.filter(provider => provider.requiresApiKey).map(provider => (
            <div key={provider.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
              <label className="text-sm font-semibold text-slate-900 dark:text-white">{provider.name} API key</label>
              <input
                type="password"
                value={draft.providerCredentials[provider.id]?.apiKey ?? ''}
                onChange={event => updateCredential(provider.id, event.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                placeholder="Enter API key"
              />
              <label className="mt-3 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <input
                  type="checkbox"
                  checked={draft.providerCredentials[provider.id]?.remember ?? true}
                  onChange={event => updateRemember(provider.id, event.target.checked)}
                />
                Remember on this device
              </label>
            </div>
          ))}
        </div>

        <div className="mt-5 space-y-3">
          {(Object.keys(ROLE_LABELS) as InferenceRoleId[]).map(role => (
            <div key={role} className="grid gap-2 rounded-xl border border-slate-200 p-3 dark:border-slate-800 md:grid-cols-[160px_1fr] md:items-center">
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{ROLE_LABELS[role]}</span>
              <select
                value={draft.roles[role].model}
                onChange={event => updateRole(role, event.target.value)}
                disabled={draft.useSameModelForHelperRoles && role !== 'answer'}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                {AI_MODELS.filter(model => model.provider !== 'ollama').map(model => (
                  <option key={`${role}-${model.id}`} value={model.id}>
                    {model.fullName} - {AI_PROVIDERS.find(provider => provider.id === model.provider)?.name}
                  </option>
                ))}
              </select>
            </div>
          ))}
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={draft.useSameModelForHelperRoles}
              onChange={event => {
                const enabled = event.target.checked;
                setDraft(current => {
                  if (!enabled) return { ...current, useSameModelForHelperRoles: false };
                  const answer = current.roles.answer;
                  return {
                    ...current,
                    useSameModelForHelperRoles: true,
                    roles: {
                      ...current.roles,
                      rewriter: { ...answer },
                      summarizer: { ...answer },
                    },
                  };
                });
              }}
            />
            Use the answer model for rewriter and memory summarizer
          </label>
        </div>

        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-between">
          <button
            type="button"
            onClick={clear}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
          >
            <Trash2 className="h-4 w-4" />
            Clear keys
          </button>
          <button
            type="button"
            onClick={save}
            disabled={!ready}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            Save setup
          </button>
        </div>
      </div>
    </div>
  );
}
