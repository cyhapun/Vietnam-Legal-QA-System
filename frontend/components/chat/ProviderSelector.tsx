import React from 'react';
import { Settings2 } from 'lucide-react';

export type Provider = 'gemini' | 'openai' | 'openrouter';

interface ProviderSelectorProps {
  provider: Provider;
  setProvider: (provider: Provider) => void;
  model: string;
  setModel: (model: string) => void;
}

// Cập nhật danh sách model chuẩn xác nhất hiện nay
const PROVIDERS = {
  gemini: {
    name: 'Google Gemini',
    models: ['gemini-2.5-flash-lite'] 
  },
  openai: {
    name: 'OpenAI',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
  },
  openrouter: {
    name: 'OpenRouter',
    models: ['anthropic/claude-3.5-sonnet', 'meta-llama/llama-3-70b-instruct']
  }
};

export function ProviderSelector({ provider, setProvider, model, setModel }: ProviderSelectorProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-white shadow-sm z-10 relative">
      <div className="flex items-center text-gray-700">
        <Settings2 className="w-5 h-5 mr-2 text-blue-600" />
        <span className="font-semibold text-sm">VietLaw AI</span>
      </div>
      
      <div className="flex space-x-3">
        <select 
          value={provider}
          onChange={(e) => {
            const newProvider = e.target.value as Provider;
            setProvider(newProvider);
            setModel(PROVIDERS[newProvider].models[0]);
          }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all cursor-pointer shadow-sm"
        >
          {Object.entries(PROVIDERS).map(([key, data]) => (
            <option key={key} value={key}>{data.name}</option>
          ))}
        </select>

        <select 
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all cursor-pointer shadow-sm min-w-[160px]"
        >
          {PROVIDERS[provider].models.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>
    </div>
  );
}