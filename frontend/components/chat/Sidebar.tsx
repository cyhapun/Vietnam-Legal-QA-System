import React from 'react';
import { Plus, MessageSquare, Trash2, Gavel, PanelLeftClose } from 'lucide-react';

export interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: number;
}

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onCloseSidebar: () => void; // Thêm prop này
}

export function Sidebar({ sessions, currentSessionId, onNewChat, onSelectSession, onDeleteSession, onCloseSidebar }: SidebarProps) {
  return (
    <div className="w-64 bg-[#171717] h-screen flex flex-col text-gray-300 font-sans font-medium border-r border-gray-800/50">
      
      {/* Thanh Header của Menu (Chứa nút tắt) */}
      <div className="h-16 flex items-center justify-between px-3">
        <span className="text-sm font-bold text-gray-200 px-2 tracking-wide">VietLaw AI</span>
        <button
          onClick={onCloseSidebar}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
          title="Đóng sidebar"
        >
          <PanelLeftClose className="w-5 h-5" />
        </button>
      </div>

      {/* Nút Tạo Chat Mới */}
      <div className="px-3 pb-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-between bg-transparent border border-gray-700/50 rounded-xl py-2.5 px-3 hover:bg-gray-800 transition-all duration-200 group"
        >
          <div className="flex items-center space-x-2">
            <div className="bg-gray-800 p-1 rounded-md group-hover:bg-blue-600 transition-colors">
              <Plus className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-medium text-gray-200">Đoạn chat mới</span>
          </div>
        </button>
      </div>

      {/* Danh sách Lịch sử Chat */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5 custom-scrollbar">
        <div className="px-2 pt-2 pb-3 text-xs font-semibold text-gray-500 mt-2">
          Hôm nay
        </div>
        
        {sessions.length === 0 ? (
          <div className="px-2 text-sm text-gray-500 italic text-center mt-4">Chưa có hội thoại nào</div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`group relative flex items-center px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                currentSessionId === session.id 
                  ? 'bg-gray-800 text-gray-100' 
                  : 'hover:bg-gray-800/50 text-gray-400 hover:text-gray-200'
              }`}
              onClick={() => onSelectSession(session.id)}
            >
              <MessageSquare className={`w-4 h-4 mr-3 flex-shrink-0 ${currentSessionId === session.id ? 'text-blue-500' : 'text-gray-500'}`} />
              
              <div className="flex-1 truncate pr-6">
                <span className="text-sm block truncate">{session.title}</span>
              </div>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.id);
                }}
                className={`absolute right-2 p-1.5 rounded-md hover:bg-gray-700 hover:text-red-400 transition-all opacity-0 group-hover:opacity-100 ${
                  currentSessionId === session.id ? 'opacity-100 text-gray-400' : ''
                }`}
                title="Xóa đoạn chat này"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Khu vực User Profile */}
      <div className="p-3 mx-2 mb-2 mt-auto">
        <div className="flex items-center space-x-3 p-2 rounded-xl hover:bg-gray-800 transition-colors cursor-pointer">
          <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-emerald-600 rounded-full flex items-center justify-center shadow-lg">
            <Gavel className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-200 truncate">VietLaw User</p>
            <p className="text-xs text-emerald-400 truncate font-medium">Free Plan</p>
          </div>
        </div>
      </div>
    </div>
  );
}