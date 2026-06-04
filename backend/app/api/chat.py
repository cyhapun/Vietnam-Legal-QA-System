"""
API Router cho endpoint /chat.
Tách từ main.py gốc — chỉ chứa logic xử lý request/response.
"""
import time
import traceback

from fastapi import APIRouter, HTTPException

from app.models import ChatRequest
from app.services.pipeline import get_pipeline
from app.services.llm import get_llm, CHAT_PROMPT, get_output_parser
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.api.chat")

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint chính: nhận câu hỏi → truy xuất pháp luật → gọi LLM → trả lời."""
    try:
        # 1. Tách câu hỏi cuối cùng
        last_message = request.messages[-1].content

        # 2. Xử lý lịch sử chat thành văn bản rõ ràng
        history_lines = []
        for msg in request.messages[:-1]:
            role_name = "🧑 USER" if msg.role == "user" else "🤖 AI"
            history_lines.append(f"{role_name}: {msg.content}")

        chat_history_str = "\n\n".join(history_lines) if history_lines else "(Không có lịch sử trò chuyện)"

        # 3. Truy xuất tài liệu pháp lý qua modular pipeline
        pipeline = get_pipeline()
        retrieved_docs, context_text = await pipeline.aretrieve(
            query=last_message,
            category=request.category,
        )
        frontend_context = pipeline.format_for_frontend(retrieved_docs)

        logger.info("=" * 60)
        logger.info("CHUẨN BỊ FEED DATA CHO LLM (CONTEXT)")
        logger.info("=" * 60)
        logger.info(context_text)

        # 4. Gọi LLM để sinh câu trả lời và đo thời gian
        start_time = time.time()

        llm = get_llm(request.model)
        rag_chain = CHAT_PROMPT | llm | get_output_parser()

        output_text = await rag_chain.ainvoke({
            "context": context_text,
            "chat_history_str": chat_history_str,
            "question": last_message
        })

        execution_time = time.time() - start_time
        logger.info("LLM trả lời trong %.2fs", execution_time)

        return {
            "text": output_text,
            "contextUsed": frontend_context
        }

    except Exception as e:
        logger.error("Lỗi xử lý chat: %s", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
