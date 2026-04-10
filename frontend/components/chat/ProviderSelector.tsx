import React from 'react';
import { Settings2 } from 'lucide-react';

interface ModelSelectorProps {
  model: string;
  setModel: (model: string) => void;
}

// Danh sách các model mã nguồn mở phổ biến trên Hugging Face
const MODELS = [
  { id: 'Qwen/Qwen3.5-9B', name: 'Qwen3.5 9B' },
  { id: 'google/gemma-4-31B-it', name: 'Gemma 4 31B IT' },
  { id: 'meta-llama/Llama-3.1-8B-Instruct', name: 'Llama 3.1 8B Instruct' },
  { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', name: 'DeepSeek R1 Distill Qwen 7B' }
];

export function ProviderSelector({ model, setModel }: ModelSelectorProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-white shadow-sm z-10 relative">
      <div className="flex items-center text-gray-700">
        <Settings2 className="w-5 h-5 mr-2 text-blue-600" />
        <span className="font-semibold text-sm">VietLaw AI</span>
      </div>
      
      <div className="flex space-x-3">
        <select 
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-all cursor-pointer shadow-sm min-w-[200px]"
        >
          {MODELS.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </div>
    </div>
  );
}