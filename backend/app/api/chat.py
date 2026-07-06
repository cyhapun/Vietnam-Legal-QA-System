"""
API Router cho endpoint /chat va /chat/stream.
Tach tu main.py goc - chi chua logic xu ly request/response.
"""
import re
import json
import time
import traceback
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import ChatRequest
from app.services.pipeline import get_pipeline
from app.services.llm import get_llm, CHAT_PROMPT, get_output_parser
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.api.chat")

router = APIRouter()

_CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\uac00-\ud7af\u3040-\u30ff]')


def _clean_chunk(text: str) -> str:
    """Loai bo ky tu CJK va khoang trang thua."""
    text = _CJK_PATTERN.sub('', text)
    return re.sub(r' +', ' ', text)


def _sse(data: dict) -> str:
    """Dinh dang mot dong Server-Sent Event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint non-streaming: nhan cau hoi -> truy xuat -> goi LLM -> tra JSON."""
    try:
        last_message = request.messages[-1].content

        history_lines = []
        for msg in request.messages[:-1]:
            role_name = "USER" if msg.role == "user" else "AI"
            history_lines.append(f"{role_name}: {msg.content}")
        chat_history_str = "\n\n".join(history_lines) if history_lines else "(Khong co lich su tro chuyen)"

        pipeline = get_pipeline()
        retrieved_docs, context_text = await pipeline.aretrieve(
            query=last_message,
            category=request.category,
        )
        frontend_context = pipeline.format_for_frontend(retrieved_docs)

        logger.info("=" * 60)
        logger.info("CHUAN BI FEED DATA CHO LLM (CONTEXT)")
        logger.info("=" * 60)
        logger.info(context_text)

        start_time = time.time()
        llm = get_llm(request.model)
        rag_chain = CHAT_PROMPT | llm | get_output_parser()

        output_text = await rag_chain.ainvoke({
            "context": context_text,
            "chat_history_str": chat_history_str,
            "question": last_message
        })

        execution_time = time.time() - start_time
        logger.info("LLM tra loi trong %.2fs", execution_time)

        output_text = _clean_chunk(output_text)

        return {"text": output_text, "contextUsed": frontend_context}

    except Exception as e:
        logger.error("Loi xu ly chat: %s", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Endpoint streaming: tra token theo tung chunk qua Server-Sent Events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            last_message = request.messages[-1].content

            history_lines = []
            for msg in request.messages[:-1]:
                role_name = "USER" if msg.role == "user" else "AI"
                history_lines.append(f"{role_name}: {msg.content}")
            chat_history_str = (
                "\n\n".join(history_lines) if history_lines
                else "(Khong co lich su tro chuyen)"
            )

            pipeline = get_pipeline()
            retrieved_docs, context_text = await pipeline.aretrieve(
                query=last_message,
                category=request.category,
            )
            frontend_context = pipeline.format_for_frontend(retrieved_docs)

            yield _sse({"type": "context", "data": frontend_context})

            llm = get_llm(request.model)
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            async for chunk in rag_chain.astream({
                "context": context_text,
                "chat_history_str": chat_history_str,
                "question": last_message,
            }):
                if chunk:
                    cleaned = _clean_chunk(chunk)
                    if cleaned:
                        yield _sse({"type": "token", "text": cleaned})

            yield _sse({"type": "done"})

        except Exception as e:
            logger.error("Loi streaming chat: %s", str(e))
            traceback.print_exc()
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
