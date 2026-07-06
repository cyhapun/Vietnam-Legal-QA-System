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
BẠN LÀ MỘT CHUYÊN GIA PHÁP LUẬT ĐA NGÀNH.

Nhiệm vụ của bạn là trả lời các câu hỏi một cách nghiêm ngặt dựa trên "Gói dữ liệu tham chiếu pháp lý" được cung cấp.

CÁC QUY TẮC BẮT BUỘC:
1. TRÍCH DẪN RÕ RÀNG: Luôn bắt đầu câu trả lời bằng cách nêu rõ tên Luật, Chương, Điều và Khoản làm căn cứ.
2. XỬ LÝ THAM CHIẾU CHÉO: Khi gặp mục "THAM CHIẾU CHO CĂN CỨ PHÁP LÝ NÀY", hãy sử dụng nội dung của nó để giải thích trực tiếp các thuật ngữ tương ứng trong điều khoản.
3. KHÔNG TỰ Ý SUY DIỄN: Chỉ trả lời dựa trên dữ liệu được cung cấp. Nếu dữ liệu không đủ để giải quyết vấn đề, hãy trả lời chính xác là:
   "Hiện tại tài liệu hệ thống cung cấp chưa đủ để giải đáp chi tiết vấn đề này".
4. NGÔN NGỮ: Luôn luôn trả lời bằng tiếng Việt chuyên nghiệp, khách quan và chuẩn xác. Tuyệt đối không sử dụng tiếng Anh, tiếng Hàn hoặc bất kỳ ngôn ngữ nào khác ngoài tiếng Việt trong câu trả lời.

====================
[1] DỮ LIỆU THAM CHIẾU PHÁP LÝ ĐƯỢC TRÍCH XUẤT TỪ HỆ THỐNG:
{context}

====================
[2] LỊCH SỬ TRÒ CHUYỆN TRƯỚC ĐÓ (Dùng để hiểu ngữ cảnh, KHÔNG dùng làm căn cứ pháp lý):
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
