"""
Quản lý kết nối LLM và System Prompt.
Tách từ main.py gốc — chỉ chứa logic liên quan đến LLM.
"""
import os

import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import (
    HUGGINGFACE_API_KEY,
    LLM_MAX_NEW_TOKENS, LLM_TEMPERATURE,
    LLM_REPETITION_PENALTY, LLM_TIMEOUT,
    INFERENCE_STRATEGY, OLLAMA_BASE_URL
)

logger = logging.getLogger(__name__)

def get_llm(model_name: str):
    """Khởi tạo kết nối với mô hình ngôn ngữ lớn (LLM) với cơ chế Hybrid Inference Fallback."""
    if not HUGGINGFACE_API_KEY:
        logger.warning("Không tìm thấy HUGGINGFACE_API_KEY. Remote LLM sẽ không hoạt động.")

    final_temperature = temperature if temperature is not None else LLM_TEMPERATURE
    final_max_tokens = max_tokens if max_tokens is not None else LLM_MAX_NEW_TOKENS

    # Nếu Frontend truyền "gemma", tự động map sang model đầy đủ
    if model_name.lower() == "gemma":
        actual_model = "google/gemma-4-31B-it:novita" 
        local_model_name = "gemma2:9b" # Map cho local Ollama
    else:
        actual_model = model_name
        local_model_name = model_name

    # 1. Khởi tạo Remote LLM
    remote_llm = ChatOpenAI(
        model=actual_model,
        api_key=HUGGINGFACE_API_KEY or "dummy_key",
        base_url="https://router.huggingface.co/v1",
        temperature=final_temperature,
        max_tokens=final_max_tokens,
        timeout=LLM_TIMEOUT,
    )

    # 2. Khởi tạo Local LLM (thông qua Ollama OpenAI API compatible endpoint)
    local_llm = ChatOpenAI(
        model=local_model_name,
        api_key="ollama",
        base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_NEW_TOKENS,
        timeout=LLM_TIMEOUT,
    )

    # 3. Wrapping with Fallbacks
    if INFERENCE_STRATEGY == "local_first":
        logger.info(f"LLM Strategy: local_first ({local_model_name} -> {actual_model})")
        return local_llm.with_fallbacks([remote_llm])
    else:
        # Default: remote_first
        logger.info(f"LLM Strategy: remote_first ({actual_model} -> {local_model_name})")
        return remote_llm.with_fallbacks([local_llm])


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
