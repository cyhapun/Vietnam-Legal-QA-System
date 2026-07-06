import React from 'react';
import { Plus, MessageSquare, Trash2, Scale, PanelLeftClose } from 'lucide-react';
import type { ChatSession } from '@/lib/types';

export type { ChatSession } from '@/lib/types';

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onCloseSidebar: () => void;
}

export function Sidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onCloseSidebar,
}: SidebarProps) {
  return (
    <div className="w-64 h-screen flex flex-col font-sans border-r border-white/5"
      style={{ background: 'linear-gradient(180deg, #0B0F19 0%, #0E1320 100%)' }}>

      {/* Header with glassmorphism */}
      <div className="h-14 flex items-center justify-between px-4 mt-1 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center shadow-lg"
            style={{ background: 'linear-gradient(135deg, #4F46E5, #2563EB)' }}
          >
            <Scale className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="text-sm font-bold text-white tracking-tight">VietLaw AI</span>
            <span className="block text-[9px] font-medium text-indigo-400 uppercase tracking-widest leading-none mt-0.5">Legal Assistant</span>
          </div>
        </div>
        <button
          onClick={onCloseSidebar}
          className="p-1.5 rounded-lg text-gray-500 hover:text-gray-200 hover:bg-white/8 transition-all"
          title="Đóng sidebar"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-2 flex-shrink-0">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-indigo-500/25 text-indigo-300 hover:text-indigo-100 hover:border-indigo-400/50 hover:bg-indigo-500/10 active:scale-98"
          style={{ background: 'rgba(79,70,229,0.07)' }}
        >
          <Plus className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Đoạn chat mới</span>
        </button>
      </div>

      {/* Divider */}
      <div className="mx-4 my-1 border-t border-white/5 flex-shrink-0" />

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5 custom-scrollbar">
        <div className="px-2 pt-1 pb-2 text-[10px] font-bold uppercase tracking-widest text-gray-600">
          Lịch sử tra cứu
        </div>

        {sessions.length === 0 ? (
          <div className="px-3 py-6 text-[12px] text-gray-600 text-center italic leading-relaxed">
            Chưa có hội thoại nào.<br />
            <span className="not-italic text-gray-500">Bắt đầu một câu hỏi mới!</span>
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = currentSessionId === session.id;
            return (
              <div
                key={session.id}
                className={`group relative flex items-center px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
                  isActive ? 'sidebar-item-active' : 'hover:bg-white/5 text-gray-400 hover:text-gray-200'
                }`}
                onClick={() => onSelectSession(session.id)}
              >
                <MessageSquare
                  className={`w-3.5 h-3.5 mr-2.5 flex-shrink-0 transition-colors ${
                    isActive ? 'text-indigo-400' : 'text-gray-600 group-hover:text-gray-400'
                  }`}
                />
                <div className="flex-1 truncate pr-6">
                  <span className={`text-[12.5px] font-medium block truncate ${isActive ? 'text-white' : ''}`}>
                    {session.title}
                  </span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id); }}
                  className="absolute right-2 p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100"
                  title="Xóa đoạn chat"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/5 flex-shrink-0">
        <p className="text-[10px] text-gray-600 text-center leading-relaxed">
          Phiên bản thử nghiệm · Dữ liệu luật VN
        </p>
      </div>
    </div>
  );
}

