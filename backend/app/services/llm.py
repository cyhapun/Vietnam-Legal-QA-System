"""
Quản lý kết nối LLM Google AI Studio với cơ chế Multi-Key & Multi-Model Fallback và System Prompt.
"""
from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import (
    GOOGLE_API_KEY,
    GOOGLE_API_KEYS,
    GOOGLE_FALLBACK_MODEL,
    GOOGLE_FALLBACK_MODELS,
    GOOGLE_MODEL,
    GOOGLE_OPENAI_BASE_URL,
    LLM_MAX_NEW_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)
from app.services.provider_registry import (
    ANSWER_ROLE,
    GOOGLE_CHAT_MODELS,
    GOOGLE_PROVIDER,
    PROVIDER_REGISTRY,
    is_supported_model,
    normalize_provider_id,
    redact_runtime_inference_config,
)

logger = logging.getLogger(__name__)


def is_google_chat_model(model_name: str) -> bool:
    """Return True for verified Google AI Studio chat model ids."""
    return (model_name or "").strip().lower() in GOOGLE_CHAT_MODELS


def parse_google_api_keys(explicit_key: Optional[str] = None) -> List[str]:
    """Phân giải danh sách Google API keys từ explicit key hoặc biến môi trường, tự động khử trùng lặp."""
    keys: List[str] = []

    if explicit_key and explicit_key.strip():
        raw_sources = [explicit_key.strip()]
    elif GOOGLE_API_KEYS and GOOGLE_API_KEYS.strip():
        raw_sources = [GOOGLE_API_KEYS.strip()]
    elif GOOGLE_API_KEY and GOOGLE_API_KEY.strip():
        raw_sources = [GOOGLE_API_KEY.strip()]
    else:
        env_keys = os.getenv("GOOGLE_API_KEYS", "") or os.getenv("GOOGLE_API_KEY", "")
        raw_sources = [env_keys.strip()] if env_keys else []

    for source in raw_sources:
        if not source:
            continue
        for part in str(source).split(","):
            cleaned = part.strip()
            if cleaned and cleaned not in keys:
                keys.append(cleaned)

    return keys


def parse_google_fallback_models(primary_model: str) -> List[str]:
    """Phân giải danh sách model dự phòng của Google, loại bỏ model chính nếu trùng."""
    raw = GOOGLE_FALLBACK_MODELS if GOOGLE_FALLBACK_MODELS is not None else os.getenv("GOOGLE_FALLBACK_MODELS", "")
    fallback_models: List[str] = []

    if not raw:
        return fallback_models

    for part in raw.split(","):
        cleaned = part.strip().lower()
        if cleaned and cleaned != primary_model.strip().lower() and cleaned not in fallback_models:
            if is_google_chat_model(cleaned):
                fallback_models.append(cleaned)
            else:
                logger.warning("Bỏ qua model dự phòng không hợp lệ: %s", cleaned)

    return fallback_models


def _make_openai_chat(
    *,
    model_name: str,
    api_key: str,
    base_url: str = GOOGLE_OPENAI_BASE_URL,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _mask_key(chat_or_key: Any) -> str:
    if isinstance(chat_or_key, str):
        k = chat_or_key
    elif hasattr(chat_or_key, "api_key") and isinstance(chat_or_key.api_key, str):
        k = chat_or_key.api_key
    elif hasattr(chat_or_key, "openai_api_key"):
        secret = chat_or_key.openai_api_key
        k = secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)
    else:
        return ""
    return f"{k[:6]}..." if len(k) >= 6 else "***"


def build_google_llm_chain(
    model_name: str,
    api_keys: List[str],
    fallback_models: List[str],
    temperature: float,
    max_tokens: int,
    timeout: float,
    enable_fallbacks: bool = True,
):
    """
    Xây dựng LLM chain với fallback đa tầng: Ưu tiên đổi Key trước, rồi mới đổi Model.
    Thứ tự ưu tiên (Key-First Priority):
    (Model_1, Key_1) -> (Model_1, Key_2) ... -> (Model_2, Key_1) -> (Model_2, Key_2) ...
    """
    if not api_keys:
        raise RuntimeError("Không có Google API Key nào được cấu hình. Vui lòng thiết lập GOOGLE_API_KEY hoặc GOOGLE_API_KEYS.")

    models_order = [model_name]
    if enable_fallbacks:
        models_order.extend(fallback_models)

    llm_instances = []
    for model in models_order:
        keys_order = api_keys if enable_fallbacks else [api_keys[0]]
        for key in keys_order:
            chat = _make_openai_chat(
                model_name=model,
                api_key=key,
                base_url=GOOGLE_OPENAI_BASE_URL,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            llm_instances.append(chat)

    primary = llm_instances[0]
    fallbacks = llm_instances[1:]

    if fallbacks:
        fallback_desc = " -> ".join(
            f"{getattr(f, 'model_name', getattr(f, 'model', ''))}:{_mask_key(f)}"
            for f in fallbacks
        )
        logger.info(
            "Khởi tạo Google LLM: Primary=(%s:%s) Fallbacks=(%s)",
            getattr(primary, "model_name", getattr(primary, "model", "")),
            _mask_key(primary),
            fallback_desc,
        )
        return primary.with_fallbacks(fallbacks)
    return primary


def _runtime_role(runtime_config, role: str):
    if runtime_config is None:
        return None
    roles = getattr(runtime_config, "roles", None)
    return roles.get(role) if roles else None


def _runtime_api_key(runtime_config, provider: str) -> str:
    if runtime_config is None:
        return ""
    return runtime_config.api_key_for(provider)


def get_llm(
    model_name: str = GOOGLE_MODEL,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    runtime_config=None,
    role: str = ANSWER_ROLE,
):
    """
    Khởi tạo kết nối LLM Google AI Studio với cơ chế Multi-Key & Multi-Model Fallback.
    """
    runtime_role = _runtime_role(runtime_config, role)
    runtime_key = _runtime_api_key(runtime_config, GOOGLE_PROVIDER) if runtime_config else ""
    use_server_fallbacks = getattr(runtime_config, "use_server_fallbacks", True)

    target_model = model_name or GOOGLE_MODEL
    explicit_key = None

    if runtime_role is not None:
        target_model = runtime_role.model
        explicit_key = runtime_key or None

    if not is_google_chat_model(target_model):
        supported = ", ".join(sorted(GOOGLE_CHAT_MODELS))
        raise ValueError(
            f"Unsupported Google model '{target_model}'. Choose one of the configured supported models: {supported}."
        )

    final_temperature = temperature if temperature is not None else LLM_TEMPERATURE
    final_max_tokens = max_tokens if max_tokens is not None else LLM_MAX_NEW_TOKENS
    final_timeout = timeout if timeout is not None else LLM_TIMEOUT

    keys = parse_google_api_keys(explicit_key)
    if not keys:
        raise RuntimeError("Không có Google API Key nào được cấu hình. Vui lòng thiết lập GOOGLE_API_KEY hoặc GOOGLE_API_KEYS.")

    fallback_models = parse_google_fallback_models(target_model)

    return build_google_llm_chain(
        model_name=target_model,
        api_keys=keys,
        fallback_models=fallback_models,
        temperature=final_temperature,
        max_tokens=final_max_tokens,
        timeout=final_timeout,
        enable_fallbacks=use_server_fallbacks,
    )


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
5. BẮT BUỘC TRÍCH DẪN (STRICT CITATION): Khi sử dụng thông tin từ dữ liệu tham chiếu, bạn PHẢI trích dẫn bằng thẻ `<cite id="[MÃ ID]">Tên Điều/Khoản</cite>`, trong đó `[MÃ ID]` CHÍNH XÁC là đoạn mã được cung cấp trong thẻ `[CĂN CỨ ID: ...]`. TUYỆT ĐỐI KHÔNG TỰ BỊA RA ID VÀ KHÔNG SỬ DỤNG ID VÍ DỤ.

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
