import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Scale, BookOpen } from 'lucide-react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`py-6 px-4 ${isUser ? 'bg-transparent' : 'bg-transparent'}`}>
      <div className={`max-w-4xl mx-auto flex space-x-4 ${isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'}`}>
        
        {/* Avatar */}
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center shadow-sm">
              <User className="w-4 h-4 text-white" />
            </div>
          ) : (
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm">
              <Scale className="w-4 h-4 text-white" />
            </div>
          )}
        </div>
        
        {/* Message Content */}
        <div className={`flex-1 min-w-0 ${isUser ? 'flex justify-end' : ''}`}>
          <div className={`inline-block max-w-[90%] ${
            isUser 
              ? 'bg-gray-100 text-gray-800 px-5 py-3.5 rounded-2xl rounded-tr-sm' 
              : 'text-gray-800'
          }`}>
            <div className={`prose prose-slate max-w-none ${isUser ? 'prose-p:leading-relaxed' : 'prose-p:leading-7 prose-headings:text-blue-900 prose-a:text-blue-600'}`}>
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>
          
          {/* RAG Context Display */}
          {!isUser && message.contextUsed && message.contextUsed.length > 0 && (
            <div className="mt-4 bg-blue-50/50 rounded-xl p-4 border border-blue-100/50 inline-block w-full">
              <div className="flex items-center text-blue-800 mb-3">
                <BookOpen className="w-4 h-4 mr-2" />
                <span className="text-xs font-bold uppercase tracking-wider">Căn cứ pháp lý trích xuất</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {message.contextUsed.map((ctx: any, idx) => {
                  // Lấy các trường metadata từ Backend mới
                  const { source, dieu, khoan } = ctx.metadata || {};
                  
                  // Xây dựng chuỗi hiển thị thông minh
                  let displayText = source || 'Tài liệu pháp lý';
                  if (dieu) displayText += ` - Điều ${dieu}`;
                  if (khoan) displayText += ` (Khoản ${khoan})`;

                  return (
                    <div 
                      key={idx} 
                      className="group inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-blue-700 border border-blue-200 hover:border-blue-400 hover:shadow-sm cursor-help transition-all"
                      title={ctx.content} // Hiển thị nội dung luật khi hover
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-2 flex-shrink-0"></span>
                      <span className="truncate max-w-[250px]">{displayText}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}