"""
Quản lý kết nối LLM và System Prompt.
Tách từ main.py gốc — chỉ chứa logic liên quan đến LLM.
"""
import os

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import (
    HUGGINGFACE_API_KEY,
    LLM_MAX_NEW_TOKENS, LLM_TEMPERATURE,
    LLM_REPETITION_PENALTY, LLM_TIMEOUT,
)


def get_llm(model_name: str) -> ChatHuggingFace:
    """Khởi tạo kết nối với mô hình ngôn ngữ lớn (LLM) qua HuggingFace."""
    if not HUGGINGFACE_API_KEY:
        raise ValueError(
            "Không tìm thấy HUGGINGFACE_API_KEY. "
            "Vui lòng cấu hình trong file .env"
        )

    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        task="text-generation",
        max_new_tokens=LLM_MAX_NEW_TOKENS,
        temperature=LLM_TEMPERATURE,
        huggingfacehub_api_token=HUGGINGFACE_API_KEY,
        do_sample=True,
        repetition_penalty=LLM_REPETITION_PENALTY,
        timeout=LLM_TIMEOUT,
    )
    return ChatHuggingFace(llm=llm)


# --- CẤU TRÚC SYSTEM PROMPT ---
CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
YOU ARE A MULTI-DISCIPLINARY LEGAL EXPERT.

Your task is to answer questions strictly based on the provided "Legal Reference Data Packages".

MANDATORY RULES:
1. CLEAR CITATION: Always begin your answer by explicitly stating the Law name, Chapter, Article, and Clause.
2. HANDLE CROSS-REFERENCES: When encountering the section "REFERENCES FOR THIS LEGAL BASIS", use its content to directly interpret and explain the corresponding terms in the clause.
3. NO ASSUMPTION: Only answer based on the provided data. If the data does not sufficiently address the issue, respond with:
   "Hiện tại tài liệu hệ thống cung cấp chưa đủ để giải đáp chi tiết vấn đề này".
4. LANGUAGE: Always respond in professional and objective Vietnamese.

====================
[1] SYSTEM-EXTRACTED LEGAL REFERENCE DATA:
{context}

====================
[2] PREVIOUS CHAT HISTORY (Dùng để hiểu ngữ cảnh, KHÔNG dùng làm căn cứ pháp lý):
{chat_history_str}
"""),
    ("human", """
> CÂU HỎI MỚI CỦA NGƯỜI DÙNG:
{question}
""")
])


def get_output_parser() -> StrOutputParser:
    """Trả về output parser cho LLM chain."""
    return StrOutputParser()
