import React from 'react';
import { Cpu } from 'lucide-react';

interface ModelSelectorProps {
  model?: string;
  setModel?: (model: string) => void;
}

export function ProviderSelector({ model = 'gemini-3.1-flash-lite' }: ModelSelectorProps) {
  return (
    <div className="relative flex items-center">
      <div 
        className="flex items-center rounded-xl border border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800 px-3 py-1.5 cursor-default select-none"
        title="Mô hình suy luận cố định: Google AI Studio - Gemini 3.1 Flash-Lite"
      >
        <Cpu className="w-3.5 h-3.5 text-blue-600 mr-2" />
        <span className="text-[12px] font-bold text-gray-700 dark:text-gray-300">
          Google AI Studio: Gemini 3.1 Flash-Lite
        </span>
      </div>
    </div>
  );
}
