import React, { useState } from 'react';
import { Plus, MessageSquare, Trash2, Scale, PanelLeftClose, Search, Moon, Sun, LibraryBig, Settings } from 'lucide-react';
import { useTheme } from 'next-themes';
import Link from 'next/link';
import { isToday, isYesterday, differenceInDays, isThisMonth } from 'date-fns';
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
  const [searchQuery, setSearchQuery] = useState('');
  const { theme, setTheme, systemTheme } = useTheme();
  
  const currentTheme = theme === 'system' ? systemTheme : theme;

  const filteredSessions = sessions.filter(s => 
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groupedSessions = filteredSessions.reduce((acc, session) => {
    const date = new Date(session.timestamp);
    let group = 'Cũ hơn';
    if (isToday(date)) group = 'Hôm nay';
    else if (isYesterday(date)) group = 'Hôm qua';
    else if (differenceInDays(new Date(), date) <= 7) group = '7 ngày trước';
    else if (isThisMonth(date)) group = 'Tháng này';

    if (!acc[group]) acc[group] = [];
    acc[group].push(session);
    return acc;
  }, {} as Record<string, ChatSession[]>);

  const groupOrder = ['Hôm nay', 'Hôm qua', '7 ngày trước', 'Tháng này', 'Cũ hơn'];

  return (
    <div className="w-64 h-screen flex flex-col font-sans border-r border-white/5 dark:border-r-gray-800 transition-colors"
      style={{ background: 'linear-gradient(180deg, #0B0F19 0%, #0E1320 100%)' }}>

      {/* Header with glassmorphism */}
      <div className="h-14 flex items-center justify-between px-4 mt-1 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20"
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
      <div className="px-3 py-2 flex-shrink-0 space-y-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-indigo-500/25 text-indigo-300 hover:text-indigo-100 hover:border-indigo-400/50 hover:bg-indigo-500/10 active:scale-98"
          style={{ background: 'rgba(79,70,229,0.07)' }}
        >
          <Plus className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Đoạn chat mới</span>
        </button>
        <Link
          href="/docs"
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-white/5 text-gray-400 hover:text-gray-200 hover:bg-white/5 active:scale-98"
        >
          <LibraryBig className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Kho Tài Liệu</span>
        </Link>
        <Link
          href="/admin"
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 transition-all duration-200 border border-white/5 text-gray-400 hover:text-gray-200 hover:bg-white/5 active:scale-98 mt-2"
        >
          <Settings className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Quản trị</span>
        </Link>
      </div>

      {/* Search Bar */}
      <div className="px-3 pb-3 flex-shrink-0">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
          <input
            type="text"
            placeholder="Tìm kiếm đoạn chat..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-9 pr-3 text-[12.5px] text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 focus:bg-white/10 transition-all"
          />
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 mb-2 border-t border-white/5 flex-shrink-0" />

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-4 custom-scrollbar">
        {filteredSessions.length === 0 ? (
          <div className="px-3 py-6 text-[12px] text-gray-600 text-center italic leading-relaxed">
            {searchQuery ? 'Không tìm thấy đoạn chat nào.' : (
              <>Chưa có hội thoại nào.<br /><span className="not-italic text-gray-500">Bắt đầu một câu hỏi mới!</span></>
            )}
          </div>
        ) : (
          groupOrder.map(group => {
            const groupSessions = groupedSessions[group];
            if (!groupSessions || groupSessions.length === 0) return null;

            return (
              <div key={group} className="space-y-0.5">
                <div className="px-2 pt-1 pb-1.5 text-[10px] font-bold uppercase tracking-widest text-gray-600">
                  {group}
                </div>
                {groupSessions.map((session) => {
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
                })}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/5 flex-shrink-0 flex items-center justify-between">
        <p className="text-[10px] text-gray-600 leading-relaxed">
          Phiên bản thử nghiệm · Dữ liệu luật VN
        </p>
        <button
          onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
          className="p-1.5 rounded-lg text-gray-500 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
          title="Chuyển chế độ giao diện"
        >
          {currentTheme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}
