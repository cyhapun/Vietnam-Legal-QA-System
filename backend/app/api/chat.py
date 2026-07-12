"""
API Router cho endpoint /chat và /chat/stream.
Tách từ main.py gốc — chỉ chứa logic xử lý request/response.
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


def _recent_messages(request: ChatRequest):
    """Return the configured messages immediately before the latest user message."""
    limit = request.historyMessages
    return request.messages[-(limit + 1):-1] if limit > 0 else []


def _filter_cited_context(output_text: str, context: list, max_citations: int) -> list:
    """Return cited contexts in citation order, capped for the client payload."""
    cited_ids = list(dict.fromkeys(re.findall(r'<cite\s+id=["\']([^"\']+)["\']>', output_text)))
    if not cited_ids:
        return context[:max_citations]
    cited_ids = cited_ids[:max_citations]
    by_id = {item.get("metadata", {}).get("id"): item for item in context}
    return [by_id[citation_id] for citation_id in cited_ids if citation_id in by_id]


def _rewrite_query(rewriter, query: str, history: str, runtime_config):
    try:
        return rewriter.rewrite(query, history, runtime_config)
    except TypeError:
        return rewriter.rewrite(query, history)

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint non-streaming: nhan cau hoi -> truy xuat -> goi LLM -> tra JSON."""
    try:
        last_message = request.messages[-1].content

        last_message = request.messages[-1].content
        session_id = request.sessionId

        from app.services.storage import get_session_summary
        from app.services.memory_manager import summarize_session

        session_data = get_session_summary(session_id) if request.enableMemory and session_id != "unknown" else None
        summary = session_data.get("summary", "") if session_data else ""

        history_lines = []
        if summary:
            history_lines.append(f"=== BỐI CẢNH TRƯỚC ĐÓ ===\n{summary}\n\n=== HỘI THOẠI GẦN NHẤT ===")
            
        for msg in _recent_messages(request): # Chỉ lấy 4 tin nhắn gần nhất
            role_name = "USER" if msg.role == "user" else "AI"
            history_lines.append(f"{role_name}: {msg.content}")
            
        chat_history_str = "\n".join(history_lines) if history_lines else "(Khong co lich su tro chuyen)"

        pipeline = get_pipeline()
        
        import asyncio
        from app.services.pipeline import _get_embedding
        from app.services.chat_logger import log_interaction
        
        # Lịch sử ngắn gọn cho rewriter (sliding window: 2 turns = 4 messages)
        recent_history_lines = []
        for msg in _recent_messages(request): # Lấy tối đa 4 tin nhắn gần nhất
            role_name = "USER" if msg.role == "user" else "AI"
            recent_history_lines.append(f"{role_name}: {msg.content}")
        recent_history_str = "\n".join(recent_history_lines) if request.useHistoryForRewriter else ""
        
        # Gọi rewriter trước để lấy rewritten query
        if request.enableQueryRewriter:
            domain, queries = await asyncio.to_thread(
                _rewrite_query,
                pipeline.rewriter,
                last_message,
                recent_history_str,
                request.inference_config,
            )
        else:
            domain, queries = "legal", [last_message]
        if domain != "chitchat":
            queries = (queries or [last_message])[:request.maxSubqueries]
        logger.info("Rewriter enabled=%s, domain=%s, queries=%s", request.enableQueryRewriter, domain, queries)
        
        query_vector = None
        if request.enableSemanticCache and domain != "chitchat":
            rewritten_query = queries[0] if queries else last_message
            embedding = _get_embedding()
            if embedding:
                try:
                    # Sinh embedding cho câu hỏi đã được viết lại
                    query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)
                    
                    # Kiểm tra cache
                    from app.services.semantic_cache import check_cache
                    cached_response = await asyncio.to_thread(check_cache, query_vector, request.cacheThreshold)
                    if cached_response:
                        logger.info("Phản hồi được lấy từ Semantic Cache.")
                        return {
                            "text": cached_response.get("response_text", ""),
                            "contextUsed": cached_response.get("context_used", [])
                        }
                except Exception as e:
                    logger.warning("Cache check failed: %s", e)

        retrieved_docs, context_text = await pipeline.aretrieve(
            query=last_message,
            k=request.candidateK,
            category=request.category,
            rerank_top_k=request.topK,
            domain=domain,
            queries=queries,
            enable_reranker=request.enableReranker,
            context_token_budget=request.contextTokenBudget
        )
        frontend_context = pipeline.format_for_frontend(retrieved_docs)

        logger.info("Đã chuẩn bị %d ký tự context (từ %d tài liệu) cho LLM", len(context_text), len(retrieved_docs))
        logger.debug("CONTEXT TEXT:\n%s", context_text)

        start_time = time.time()
        try:
            llm = get_llm(
                model_name=request.model, 
                temperature=request.temperature, 
                max_tokens=request.maxTokens,
                timeout=request.llmTimeout,
                runtime_config=request.inference_config,
                role="answer",
            )
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            output_text = await rag_chain.ainvoke({
                "context": context_text,
                "chat_history_str": chat_history_str,
                "question": last_message
            })
        except Exception as llm_exc:
            logger.error("All LLM providers failed: %s", llm_exc)
            raise HTTPException(status_code=503, detail="Tất cả các dịch vụ suy luận (LLM) đều không khả dụng. Vui lòng thử lại sau.")

        execution_time = time.time() - start_time
        logger.info("LLM tra loi trong %.2fs", execution_time)

        output_text = _clean_chunk(output_text)

        frontend_context = _filter_cited_context(
            output_text, frontend_context, request.maxCitations
        )

        if query_vector and domain != "chitchat" and "Hiện tại hệ thống chưa thể gọi mô hình" not in output_text:
            try:
                from app.services.semantic_cache import update_cache
                await asyncio.to_thread(
                    update_cache,
                    query_vector=query_vector,
                    original_query=last_message,
                    response_text=output_text,
                    context_used=frontend_context,
                    retrieved_doc_ids=[doc.metadata.get("id") for doc in retrieved_docs if doc.metadata.get("id")]
                )
            except Exception as e:
                logger.warning("Failed to update cache: %s", e)

        # Log interaction asynchronously
        asyncio.create_task(
            asyncio.to_thread(log_interaction, "unknown", last_message, output_text)
        )
        
        # Summarize memory asynchronously
        if request.enableMemory and session_id != "unknown":
            asyncio.create_task(summarize_session(
                session_id,
                last_message,
                output_text,
                runtime_config=request.inference_config,
            ))

        return {
            "text": output_text,
            "contextUsed": frontend_context
        }

    except HTTPException:
        raise
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

            last_message = request.messages[-1].content
            session_id = request.sessionId
            
            from app.services.storage import get_session_summary
            from app.services.memory_manager import summarize_session

            session_data = get_session_summary(session_id) if request.enableMemory and session_id != "unknown" else None
            summary = session_data.get("summary", "") if session_data else ""

            history_lines = []
            if summary:
                history_lines.append(f"=== BỐI CẢNH TRƯỚC ĐÓ ===\n{summary}\n\n=== HỘI THOẠI GẦN NHẤT ===")
                
            for msg in _recent_messages(request):
                role_name = "USER" if msg.role == "user" else "AI"
                history_lines.append(f"{role_name}: {msg.content}")
                
            chat_history_str = (
                "\n".join(history_lines) if history_lines
                else "(Khong co lich su tro chuyen)"
            )

            pipeline = get_pipeline()
            
            import asyncio
            from app.services.pipeline import _get_embedding
            from app.services.chat_logger import log_interaction
            
            recent_history_lines = []
            for msg in _recent_messages(request):
                role_name = "USER" if msg.role == "user" else "AI"
                recent_history_lines.append(f"{role_name}: {msg.content}")
            recent_history_str = "\n".join(recent_history_lines) if request.useHistoryForRewriter else ""
            
            if request.enableQueryRewriter:
                domain, queries = await asyncio.to_thread(
                    _rewrite_query,
                    pipeline.rewriter,
                    last_message,
                    recent_history_str,
                    request.inference_config,
                )
            else:
                domain, queries = "legal", [last_message]
            if domain != "chitchat":
                queries = (queries or [last_message])[:request.maxSubqueries]
            logger.info("Stream rewriter enabled=%s, domain=%s, queries=%s", request.enableQueryRewriter, domain, queries)
            
            query_vector = None
            if request.enableSemanticCache and domain != "chitchat":
                rewritten_query = queries[0] if queries else last_message
                embedding = _get_embedding()
                if embedding:
                    try:
                        query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)
                        from app.services.semantic_cache import check_cache
                        cached_response = await asyncio.to_thread(check_cache, query_vector, request.cacheThreshold)
                        if cached_response:
                            logger.info("Stream: Phản hồi được lấy từ Semantic Cache.")
                            frontend_context = cached_response.get("context_used", [])
                            yield _sse({"type": "context", "data": frontend_context})
                            
                            cached_text = cached_response.get("response_text", "")
                            words = cached_text.split(" ")
                            for i, word in enumerate(words):
                                yield _sse({"type": "token", "text": word + (" " if i < len(words) - 1 else "")})
                                await asyncio.sleep(0.01)
                                
                            yield _sse({"type": "done"})
                            return
                    except Exception as e:
                        logger.warning("Stream Cache check failed: %s", e)

            retrieved_docs, context_text = await pipeline.aretrieve(
                query=last_message,
                k=request.candidateK,
                category=request.category,
                rerank_top_k=request.topK,
                domain=domain,
                queries=queries,
                enable_reranker=request.enableReranker,
                context_token_budget=request.contextTokenBudget
            )
            frontend_context = pipeline.format_for_frontend(retrieved_docs)

            yield _sse({"type": "context", "data": frontend_context})

            llm = get_llm(
                model_name=request.model, 
                temperature=request.temperature, 
                max_tokens=request.maxTokens,
                timeout=request.llmTimeout,
                runtime_config=request.inference_config,
                role="answer",
            )
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            accumulated_text = ""
            async for chunk in rag_chain.astream({
                "context": context_text,
                "chat_history_str": chat_history_str,
                "question": last_message,
            }):
                if chunk:
                    cleaned = _clean_chunk(chunk)
                    if cleaned:
                        accumulated_text += cleaned
                        yield _sse({"type": "token", "text": cleaned})

            frontend_context = _filter_cited_context(
                accumulated_text, frontend_context, request.maxCitations
            )
            yield _sse({"type": "context", "data": frontend_context})
            if query_vector and domain != "chitchat" and "Hiện tại hệ thống chưa thể gọi mô hình" not in accumulated_text:
                try:
                    from app.services.semantic_cache import update_cache
                    await asyncio.to_thread(
                        update_cache,
                        query_vector=query_vector,
                        original_query=last_message,
                        response_text=accumulated_text,
                        context_used=frontend_context,
                        retrieved_doc_ids=[doc.metadata.get("id") for doc in retrieved_docs if doc.metadata.get("id")]
                    )
                except Exception as e:
                    logger.warning("Stream Failed to update cache: %s", e)

            # Log interaction asynchronously
            asyncio.create_task(
                asyncio.to_thread(log_interaction, "unknown", last_message, accumulated_text)
            )

            # Summarize memory asynchronously
            if request.enableMemory and session_id != "unknown":
                asyncio.create_task(summarize_session(
                    session_id,
                    last_message,
                    accumulated_text,
                    runtime_config=request.inference_config,
                ))

            yield _sse({"type": "done"})

        except Exception as e:
            logger.error("Loi streaming chat: %s", str(e))
            traceback.print_exc()
            yield _sse({"type": "error", "message": "Dịch vụ suy luận gặp sự cố: " + str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/chat/session/{session_id}")
async def delete_session(session_id: str):
    """Xóa lịch sử trò chuyện của một session cụ thể khỏi hệ thống."""
    if not session_id or session_id == "unknown":
        raise HTTPException(status_code=400, detail="Invalid session_id")
    
    try:
        import asyncio
        from app.services.chat_logger import delete_chat_logs
        from app.services.storage import delete_session_summary
        
        # Execute deletions concurrently
        await asyncio.gather(
            asyncio.to_thread(delete_chat_logs, session_id),
            asyncio.to_thread(delete_session_summary, session_id)
        )
        
        return {"status": "success", "message": f"Session {session_id} deleted."}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")
