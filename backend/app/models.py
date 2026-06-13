"""
Pydantic models cho API request/response.
Tách riêng để dễ tái sử dụng và test.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class Message(BaseModel):
    """Một tin nhắn trong lịch sử chat."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Dữ liệu gửi lên từ Frontend khi user đặt câu hỏi."""
    messages: List[Message]
    model: str
    category: str = "all"  # Lĩnh vực pháp luật để lọc tài liệu


class ChatResponse(BaseModel):
    """Dữ liệu trả về cho Frontend sau khi LLM trả lời."""
    text: str
    contextUsed: List[Dict[str, Any]]
