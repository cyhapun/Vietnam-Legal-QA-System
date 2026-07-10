"""
Pydantic models cho API request/response.
Tách riêng để dễ tái sử dụng và test.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Một tin nhắn trong lịch sử chat."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Dữ liệu gửi lên từ Frontend khi user đặt câu hỏi."""
    messages: List[Message]
    model: str
    sessionId: Optional[str] = "unknown"
    category: str = "all"  # Lĩnh vực pháp luật để lọc tài liệu
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    topK: Optional[int] = Field(default=None, ge=1, le=20)
    candidateK: int = Field(default=60, ge=10, le=100)
    cacheThreshold: float = Field(default=0.95, ge=0.8, le=0.99)
    maxSubqueries: int = Field(default=3, ge=1, le=5)
    historyMessages: int = Field(default=4, ge=0, le=10)
    enableQueryRewriter: bool = True
    enableReranker: bool = True
    enableSemanticCache: bool = True
    enableMemory: bool = True


class ChatResponse(BaseModel):
    """Dữ liệu trả về cho Frontend sau khi LLM trả lời."""
    text: str
    contextUsed: List[Dict[str, Any]]
