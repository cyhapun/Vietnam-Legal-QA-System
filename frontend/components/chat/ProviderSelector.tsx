import React from 'react';
import { Cpu } from 'lucide-react';

interface ModelSelectorProps {
  model?: string;
  setModel?: (model: string) => void;
}

export function ProviderSelector({ model = 'gemini-3.1-flash-lite' }: ModelSelectorProps) {
  return (
    <div className="relative flex items-center shrink-0">
      <div
        className="flex items-center rounded-xl border border-gray-100 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-2.5 sm:px-3 py-1.5 cursor-default select-none whitespace-nowrap"
        title="Mô hình suy luận cố định: Google AI Studio - Gemini 3.1 Flash-Lite"
      >
        <Cpu className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 mr-1.5 sm:mr-2 shrink-0" />
        <span className="text-[11.5px] sm:text-[12px] font-bold text-gray-700 dark:text-gray-300">
          <span className="sm:hidden">Gemini 3.1</span>
          <span className="hidden sm:inline md:hidden">Gemini 3.1 Flash-Lite</span>
          <span className="hidden md:inline">Google AI Studio: Gemini 3.1 Flash-Lite</span>
        </span>
      </div>
    </div>
  );
}
