/**
 * Loading spinner component — hiển thị khi đang chờ LLM trả lời.
 * Tách từ ChatInterface.tsx để tái sử dụng.
 */
import React from 'react';
import Image from 'next/image';

export function LoadingSpinner() {
  return (
    <div className="py-6 px-4">
      <div className="max-w-4xl mx-auto flex space-x-4 items-center">
        <div className="relative w-8 h-8 flex-shrink-0 flex items-center justify-center">
          <Image
            src="/logo.png"
            alt="VietLaw AI Loading"
            width={32}
            height={32}
            className="w-full h-full object-contain drop-shadow-sm animate-pulse"
            unoptimized
          />
        </div>
        <div className="flex space-x-1.5 items-center px-4 py-3">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}
