"""FastAPI router for /chat, /chat/stream, and session history endpoints."""
from __future__ import annotations

import json
import re
import time
import traceback
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import (
    CHAT_STORAGE_MODE,
    GOOGLE_FALLBACK_MODEL,
    LLM_MAX_NEW_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    PIPELINE_TIMING_ENABLED,
)
from app.models import ChatRequest
from app.services.pipeline import get_pipeline
from app.services.llm import get_llm, CHAT_PROMPT, get_output_parser
from app.services.embedding.errors import (
    EmbeddingAuthError,
    EmbeddingServiceError,
)
from app.services.pipeline_timing import (
    PipelineTimingCollector,
    reset_current_timing,
    sanitize_request_id,
    set_current_timing,
)
from app.services.chat_orchestrator import (
    prepare_turn_context,
    retrieve_turn_context,
    finalize_turn,
    persist_completed_turn,
    get_recent_messages,
    filter_cited_context,
    rewrite_query,
    persist_turn,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.api.chat")

router = APIRouter()

_CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\uac00-\ud7af\u3040-\u30ff]')

# Backward compatibility aliases
_recent_messages = get_recent_messages
_filter_cited_context = filter_cited_context
_rewrite_query = rewrite_query
_persist_turn = persist_turn
_persist_completed_turn = persist_completed_turn


def _clean_chunk(text: str) -> str:
    """Loại bỏ ký tự CJK và khoảng trắng thừa."""
    text = _CJK_PATTERN.sub('', text)
    return re.sub(r' +', ' ', text)


def _sse(data: dict) -> str:
    """Định dạng một dòng Server-Sent Event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _embedding_error_status(exc: EmbeddingServiceError) -> int:
    return 401 if isinstance(exc, EmbeddingAuthError) else 503


def _llm_error_detail(model_name: str | None, exc: Exception) -> str:
    """Return a user-safe LLM error message without exposing credentials."""
    text = str(exc)
    lowered = text.lower()
    if "unsupported google model" in lowered:
        return text
    if "404" in lowered or "not_found" in lowered or "no longer available" in lowered:
        return (
            f"LLM provider rejected model '{model_name}'. "
            "Choose a currently supported model and retry."
        )
    return "Tất cả các dịch vụ suy luận (LLM) đều không khả dụng. Vui lòng thử lại sau."


def _new_timing(http_request: Request, endpoint: str, streaming: bool) -> PipelineTimingCollector:
    return PipelineTimingCollector(
        request_id=sanitize_request_id(http_request.headers.get("x-request-id")),
        endpoint=endpoint,
        streaming=streaming,
        enabled=PIPELINE_TIMING_ENABLED,
    )


@router.post("/chat")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    """Endpoint non-streaming: nhận câu hỏi -> truy xuất -> gọi LLM -> trả JSON."""
    timing = _new_timing(http_request, "/chat", streaming=False)
    timing_token = set_current_timing(timing if PIPELINE_TIMING_ENABLED else None)
    outcome = "success"
    try:
        pipeline = get_pipeline()
        turn = await prepare_turn_context(request, pipeline)

        # Semantic cache hit -> trả về ngay lập tức
        if turn.cached_response:
            logger.info("Phản hồi được lấy từ Semantic Cache.")
            cached_text = turn.cached_response.get("response_text", "")
            cached_context = turn.cached_response.get("context_used", [])
            await _persist_completed_turn(
                request,
                turn.session_id,
                turn.last_message,
                cached_text,
                cached_context,
                session_title=turn.session_title,
            )
            return {
                "text": cached_text,
                "contextUsed": cached_context,
                "sessionTitle": turn.session_title,
            }

        retrieved_docs, context_text, frontend_context = await retrieve_turn_context(
            pipeline=pipeline,
            last_message=turn.last_message,
            domain=turn.domain,
            queries=turn.queries,
            category=request.category,
            enable_reranker=turn.enable_reranker,
            timing=timing,
        )

        logger.info("Đã chuẩn bị %d ký tự context (từ %d tài liệu) cho LLM", len(context_text), len(retrieved_docs))
        logger.debug("CONTEXT TEXT:\n%s", context_text)

        model_name = request.model or GOOGLE_FALLBACK_MODEL
        try:
            llm = get_llm(
                model_name=model_name,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_NEW_TOKENS,
                timeout=LLM_TIMEOUT,
                role="answer",
            )
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            with timing.stage("llm_generation"):
                output_text = await rag_chain.ainvoke({
                    "context": context_text,
                    "chat_history_str": turn.chat_history_str,
                    "question": turn.last_message,
                })
        except Exception as llm_exc:
            logger.error("All LLM providers failed: %s", llm_exc)
            outcome = "error"
            raise HTTPException(status_code=503, detail=_llm_error_detail(model_name, llm_exc))

        logger.info("LLM response generated")
        cleaned_text = _clean_chunk(output_text)

        final_text, final_context = await finalize_turn(
            request=request,
            session_id=turn.session_id,
            last_message=turn.last_message,
            raw_text=cleaned_text,
            frontend_context=frontend_context,
            query_vector=turn.query_vector,
            domain=turn.domain,
            retrieved_docs=retrieved_docs,
            persist_turn_fn=_persist_completed_turn,
            session_title=turn.session_title,
        )

        return {
            "text": final_text,
            "contextUsed": final_context,
            "sessionTitle": turn.session_title,
        }

    except EmbeddingServiceError as e:
        outcome = "error"
        raise HTTPException(status_code=_embedding_error_status(e), detail=str(e))
    except ValueError as e:
        outcome = "error"
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        outcome = "error"
        raise
    except Exception as e:
        outcome = "error"
        logger.error("Lỗi xử lý chat: %s", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        timing.emit_once(outcome)
        reset_current_timing(timing_token)


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest, http_request: Request):
    """Endpoint streaming: trả token theo từng chunk qua Server-Sent Events."""
    timing = _new_timing(http_request, "/chat/stream", streaming=True)

    async def event_generator() -> AsyncGenerator[str, None]:
        timing_token = set_current_timing(timing if PIPELINE_TIMING_ENABLED else None)
        outcome = "success"
        try:
            pipeline = get_pipeline()
            turn = await prepare_turn_context(request, pipeline)

            if turn.session_title:
                yield _sse({"type": "title", "title": turn.session_title})

            # Semantic cache hit -> stream từng từ nhanh chóng
            if turn.cached_response:
                logger.info("Stream: Phản hồi được lấy từ Semantic Cache.")
                cached_context = turn.cached_response.get("context_used", [])
                yield _sse({"type": "context", "data": cached_context})

                cached_text = turn.cached_response.get("response_text", "")
                words = cached_text.split(" ")
                for i, word in enumerate(words):
                    yield _sse({"type": "token", "text": word + (" " if i < len(words) - 1 else "")})
                    await asyncio.sleep(0.01)

                await _persist_completed_turn(
                    request,
                    turn.session_id,
                    turn.last_message,
                    cached_text,
                    cached_context,
                    session_title=turn.session_title,
                )
                yield _sse({"type": "done"})
                return

            retrieved_docs, context_text, frontend_context = await retrieve_turn_context(
                pipeline=pipeline,
                last_message=turn.last_message,
                domain=turn.domain,
                queries=turn.queries,
                category=request.category,
                enable_reranker=turn.enable_reranker,
                timing=timing,
            )

            yield _sse({"type": "context", "data": frontend_context})

            model_name = request.model or GOOGLE_FALLBACK_MODEL
            llm = get_llm(
                model_name=model_name,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_NEW_TOKENS,
                timeout=LLM_TIMEOUT,
                role="answer",
            )
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            accumulated_text = ""
            llm_start_ns = time.perf_counter_ns()
            first_token_seen = False
            with timing.stage("llm_generation"):
                async for chunk in rag_chain.astream({
                    "context": context_text,
                    "chat_history_str": turn.chat_history_str,
                    "question": turn.last_message,
                }):
                    if chunk:
                        cleaned = _clean_chunk(chunk)
                        if cleaned:
                            if not first_token_seen:
                                first_token_seen = True
                                timing.add_duration(
                                    "llm_time_to_first_token",
                                    (time.perf_counter_ns() - llm_start_ns) / 1_000_000,
                                )
                                timing.mark_first_token()
                            accumulated_text += cleaned
                            yield _sse({"type": "token", "text": cleaned})

            final_text, final_context = await finalize_turn(
                request=request,
                session_id=turn.session_id,
                last_message=turn.last_message,
                raw_text=accumulated_text,
                frontend_context=frontend_context,
                query_vector=turn.query_vector,
                domain=turn.domain,
                retrieved_docs=retrieved_docs,
                persist_turn_fn=_persist_completed_turn,
                session_title=turn.session_title,
            )

            yield _sse({"type": "context", "data": final_context})
            yield _sse({"type": "done"})

        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except EmbeddingServiceError as e:
            outcome = "error"
            yield _sse({"type": "error", "message": str(e)})
        except ValueError as e:
            outcome = "error"
            yield _sse({"type": "error", "message": str(e)})
        except Exception as e:
            outcome = "error"
            logger.error("Lỗi streaming chat: %s", str(e))
            traceback.print_exc()
            current_model = model_name if 'model_name' in locals() else None
            yield _sse({"type": "error", "message": _llm_error_detail(current_model, e)})
        finally:
            timing.emit_once(outcome)
            reset_current_timing(timing_token)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions")
async def get_sessions():
    """Trả về danh sách tất cả sessions từ PostgreSQL."""
    if CHAT_STORAGE_MODE == "browser":
        return {"storageMode": "browser", "sessions": []}
    from app.services.storage import list_sessions
    return list_sessions()


@router.get("/chat/session/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Trả về tất cả tin nhắn của một session từ PostgreSQL."""
    if CHAT_STORAGE_MODE == "browser":
        return {"storageMode": "browser", "messages": []}
    from app.services.storage import get_session_messages
    return get_session_messages(session_id)


@router.delete("/chat/session/{session_id}")
async def delete_session(session_id: str):
    """Xóa lịch sử trò chuyện của một session cụ thể khỏi hệ thống."""
    if not session_id or session_id == "unknown":
        raise HTTPException(status_code=400, detail="Invalid session_id")
    if CHAT_STORAGE_MODE == "browser":
        return {"status": "skipped", "storageMode": "browser"}

    try:
        from app.services.storage import delete_session_summary
        await asyncio.to_thread(delete_session_summary, session_id)
        return {"status": "success", "message": f"Session {session_id} deleted."}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")
