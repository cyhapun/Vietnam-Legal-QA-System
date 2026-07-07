"""
Quản lý kết nối LLM và System Prompt.
Tách từ main.py gốc — chỉ chứa logic liên quan đến LLM.
"""
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import (
    HUGGINGFACE_API_KEY,
    LLM_MAX_NEW_TOKENS, LLM_TEMPERATURE,
    LLM_REPETITION_PENALTY, LLM_TIMEOUT,
)


def get_llm(model_name: str):
    """Khởi tạo kết nối với mô hình ngôn ngữ lớn (LLM) qua HuggingFace Router (OpenAI compatible)."""
    if not HUGGINGFACE_API_KEY:
        raise ValueError(
            "Không tìm thấy HUGGINGFACE_API_KEY. "
            "Vui lòng cấu hình trong file .env"
        )

    # Nếu Frontend truyền "gemma", tự động map sang model đầy đủ
    if model_name.lower() == "gemma":
        actual_model = "google/gemma-4-31B-it:novita" # or "google/gemma-7b-it" based on what user requested, actually the user snippet specifically says "google/gemma-4-31B-it:novita"
    else:
        actual_model = model_name

    llm = ChatOpenAI(
        model=actual_model,
        api_key=HUGGINGFACE_API_KEY,
        base_url="https://router.huggingface.co/v1",
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_NEW_TOKENS,
        timeout=LLM_TIMEOUT,
    )
    return llm


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
5. STRICT CITATION FORMAT: Whenever you use a provided context, you MUST cite it using the exact XML tag format `<cite id="[ID]">Tên Điều/Khoản</cite>`, where `[ID]` is the ID provided in `[CĂN CỨ ID: ...]`. Example: `<cite id="luat_xay_dung_123">Khoản 1 Điều 5</cite>`.

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
