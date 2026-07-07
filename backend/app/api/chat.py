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
        
        import asyncio
        from app.services.pipeline import _get_embedding
        from app.services.semantic_cache import check_cache, update_cache
        from app.services.chat_logger import log_interaction
        
        # Lịch sử ngắn gọn cho rewriter (sliding window: 2 turns = 4 messages)
        recent_history_lines = []
        for msg in request.messages[-5:-1]: # Lấy tối đa 4 tin nhắn gần nhất
            role_name = "USER" if msg.role == "user" else "AI"
            recent_history_lines.append(f"{role_name}: {msg.content}")
        recent_history_str = "\n".join(recent_history_lines) if recent_history_lines else ""
        
        # Gọi rewriter trước để lấy rewritten query
        domain, queries = await asyncio.to_thread(pipeline.rewriter.rewrite, last_message, recent_history_str)
        logger.info("Rewriter domain: %s, queries: %s", domain, queries)
        
        query_vector = None
        if domain != "chitchat":
            rewritten_query = queries[0] if queries else last_message
            embedding = _get_embedding()
            if embedding:
                try:
                    # Sinh embedding cho câu hỏi đã được viết lại
                    query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)
                    
                    # Kiểm tra cache
                    cached_response = await asyncio.to_thread(check_cache, query_vector)
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
            category=request.category,
            rerank_top_k=request.topK,
            domain=domain,
            queries=queries
        )
        frontend_context = pipeline.format_for_frontend(retrieved_docs)

        logger.info("Đã chuẩn bị %d ký tự context (từ %d tài liệu) cho LLM", len(context_text), len(retrieved_docs))
        logger.debug("CONTEXT TEXT:\n%s", context_text)

        start_time = time.time()
        try:
            llm = get_llm(
                model_name=request.model, 
                temperature=request.temperature, 
                max_tokens=request.maxTokens
            )
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            output_text = await rag_chain.ainvoke({
                "context": context_text,
                "chat_history_str": chat_history_str,
                "question": last_message
            })
        except Exception as llm_exc:
            logger.warning("LLM unavailable, falling back to retrieved context: %s", llm_exc)
            output_text = (
                "Hiện tại hệ thống chưa thể gọi mô hình sinh câu trả lời, "
                "nhưng đã tìm thấy tài liệu liên quan. Vui lòng xem contextUsed để tham khảo."
            )

        execution_time = time.time() - start_time
        logger.info("LLM tra loi trong %.2fs", execution_time)

        output_text = _clean_chunk(output_text)

        # 5. Lọc context theo các ID được trích dẫn (Strict Citation Mechanism)
        cited_ids = set(re.findall(r'<cite\s+id=["\']([^"\']+)["\']>', output_text))
        if cited_ids:
            filtered_context = [ctx for ctx in frontend_context if ctx.get("metadata", {}).get("id") in cited_ids]
            frontend_context = filtered_context
        else:
            # Nếu LLM không trích dẫn gì, có thể xóa context rác
            # Để an toàn cho các trường hợp LLM fallback (lỗi), ta có thể giữ nguyên tất cả hoặc làm rỗng.
            # Ở đây chọn làm rỗng khi gọi LLM thành công nhưng không có trích dẫn,
            # Nếu có lỗi (ở phần except), ta vẫn giữ nguyên frontend_context.
            if "Hiện tại hệ thống chưa thể gọi mô hình" not in output_text:
                frontend_context = []

        if query_vector and domain != "chitchat" and "Hiện tại hệ thống chưa thể gọi mô hình" not in output_text:
            try:
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

        return {
            "text": output_text,
            "contextUsed": frontend_context
        }

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
            
            import asyncio
            from app.services.pipeline import _get_embedding
            from app.services.semantic_cache import check_cache, update_cache
            from app.services.chat_logger import log_interaction
            
            recent_history_lines = []
            for msg in request.messages[-5:-1]:
                role_name = "USER" if msg.role == "user" else "AI"
                recent_history_lines.append(f"{role_name}: {msg.content}")
            recent_history_str = "\n".join(recent_history_lines) if recent_history_lines else ""
            
            domain, queries = await asyncio.to_thread(pipeline.rewriter.rewrite, last_message, recent_history_str)
            logger.info("Stream Rewriter domain: %s, queries: %s", domain, queries)
            
            query_vector = None
            if domain != "chitchat":
                rewritten_query = queries[0] if queries else last_message
                embedding = _get_embedding()
                if embedding:
                    try:
                        query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)
                        cached_response = await asyncio.to_thread(check_cache, query_vector)
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
                category=request.category,
                rerank_top_k=request.topK,
                domain=domain,
                queries=queries
            )
            frontend_context = pipeline.format_for_frontend(retrieved_docs)

            yield _sse({"type": "context", "data": frontend_context})

            llm = get_llm(
                model_name=request.model, 
                temperature=request.temperature, 
                max_tokens=request.maxTokens
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

            if query_vector and domain != "chitchat" and "Hiện tại hệ thống chưa thể gọi mô hình" not in accumulated_text:
                try:
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
