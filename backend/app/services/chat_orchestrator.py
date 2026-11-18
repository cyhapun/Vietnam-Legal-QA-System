"""Shared turn orchestrator for non-streaming and SSE streaming legal RAG requests."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from app.config import (
    CHAT_STORAGE_MODE,
    CONTEXT_TOKEN_BUDGET,
    ENABLE_SEMANTIC_CACHE,
    HISTORY_MESSAGES,
    MAX_CITATIONS,
    MAX_SUBQUERIES,
    PIPELINE_CONFIG,
    RETRIEVER_CANDIDATE_K,
    RETRIEVER_K,
    SEMANTIC_CACHE_THRESHOLD,
)
from app.models import ChatRequest
from app.services.answer_validation import validate_generated_citations
from app.services.embedding.errors import EmbeddingServiceError
from app.services.memory_manager import summarize_session
from app.services.pipeline import RAGPipeline, _get_embedding, get_pipeline
from app.services.pipeline_timing import PipelineTimingCollector
from app.services.semantic_cache import check_cache, update_cache
from app.services.storage import (
    ensure_session_exists,
    get_session_summary,
    save_chat_message,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.orchestrator")


@dataclass
class PreparedTurnContext:
    session_id: str
    last_message: str
    chat_history_str: str
    domain: str
    queries: List[str]
    enable_reranker: bool
    session_title: Optional[str] = None
    query_vector: Optional[List[float]] = None
    cached_response: Optional[Dict[str, Any]] = None


def get_recent_messages(request: ChatRequest):
    """Return configured messages immediately before the latest user message."""
    limit = HISTORY_MESSAGES
    return request.messages[-(limit + 1):-1] if limit > 0 else []


def filter_cited_context(output_text: str, context: list, max_citations: int = MAX_CITATIONS) -> list:
    """Return cited contexts in citation order, capped for the client payload."""
    cited_ids = list(dict.fromkeys(re.findall(r'<cite\s+id=["\']([^"\']+)["\']>', output_text)))
    if not cited_ids:
        return context[:max_citations]
    cited_ids = cited_ids[:max_citations]
    by_id = {item.get("metadata", {}).get("id"): item for item in context}
    valid_citations = [by_id[citation_id] for citation_id in cited_ids if citation_id in by_id]
    if not valid_citations:
        return context[:max_citations]
    return valid_citations


def rewrite_query(rewriter, query: str, history: str) -> Tuple[str, List[str], Optional[str]]:
    try:
        res = rewriter.rewrite(query, history)
    except TypeError:
        res = rewriter.rewrite(query)

    if hasattr(res, "domain") and hasattr(res, "queries"):
        return res.domain, res.queries, getattr(res, "title", None)
    if isinstance(res, tuple):
        if len(res) >= 3:
            return res[0], res[1], res[2]
        if len(res) == 2:
            return res[0], res[1], None
    return "legal", [query], None


async def persist_turn(
    session_id: str,
    session_title: str,
    user_msg_id: str,
    user_content: str,
    ai_msg_id: str,
    ai_content: str,
    ai_context: list,
    user_time: datetime,
    ai_time: datetime,
):
    """Persist chat turn sequentially to PostgreSQL."""
    try:
        await asyncio.to_thread(ensure_session_exists, session_id, session_title)
        await asyncio.to_thread(save_chat_message, session_id, user_msg_id, "user", user_content, [], user_time)
        await asyncio.to_thread(save_chat_message, session_id, ai_msg_id, "assistant", ai_content, ai_context, ai_time)
    except Exception as e:
        logger.error("Failed to persist chat turn sequentially for session %s: %s", session_id, e)


async def persist_completed_turn(
    request: ChatRequest,
    session_id: str,
    user_content: str,
    ai_content: str,
    ai_context: list,
    session_title: Optional[str] = None,
):
    """Persist a finished turn before client treats it as complete."""
    if CHAT_STORAGE_MODE != "postgres" or session_id == "unknown":
        return

    import uuid as _uuid

    user_msg_id = request.messageId or str(_uuid.uuid4())
    ai_msg_id = str(_uuid.uuid4())
    user_time = datetime.utcnow()
    ai_time = user_time + timedelta(milliseconds=10)
    title_to_use = session_title or request.sessionTitle or "Cuoc tro chuyen moi"
    await persist_turn(
        session_id=session_id,
        session_title=title_to_use,
        user_msg_id=user_msg_id,
        user_content=user_content,
        ai_msg_id=ai_msg_id,
        ai_content=ai_content,
        ai_context=ai_context,
        user_time=user_time,
        ai_time=ai_time,
    )
    if session_title and session_title != request.sessionTitle:
        from app.services.storage import update_session_title
        await asyncio.to_thread(update_session_title, session_id, session_title)


async def prepare_turn_context(
    request: ChatRequest,
    pipeline: RAGPipeline,
) -> PreparedTurnContext:
    """Chuẩn bị lịch sử hội thoại, chạy query rewriting và kiểm tra Semantic Cache."""
    last_message = request.messages[-1].content
    session_id = request.sessionId

    session_data = (
        get_session_summary(session_id)
        if CHAT_STORAGE_MODE == "postgres" and session_id != "unknown"
        else None
    )
    summary = session_data.get("summary", "") if session_data else ""

    history_lines = []
    if summary:
        history_lines.append(f"=== BỐI CẢNH TRƯỚC ĐÓ ===\n{summary}\n\n=== HỘI THOẠI GẦN NHẤT ===")

    recent_msgs = get_recent_messages(request)
    for msg in recent_msgs:
        role_name = "USER" if msg.role == "user" else "AI"
        history_lines.append(f"{role_name}: {msg.content}")

    chat_history_str = "\n".join(history_lines) if history_lines else "(Khong co lich su tro chuyen)"

    recent_history_lines = [
        f"{'USER' if msg.role == 'user' else 'AI'}: {msg.content}"
        for msg in recent_msgs
    ]
    recent_history_str = "\n".join(recent_history_lines)

    # Query Rewriting
    enable_query_rewriter = PIPELINE_CONFIG.get("rewriter", "none") != "none"
    generated_title = None
    if enable_query_rewriter:
        domain, queries, generated_title = await asyncio.to_thread(
            rewrite_query,
            pipeline.rewriter,
            last_message,
            recent_history_str,
        )
    else:
        domain, queries = "legal", [last_message]

    if domain != "chitchat":
        queries = (queries or [last_message])[:MAX_SUBQUERIES]

    logger.info("Rewriter enabled=%s, domain=%s, queries=%s, title=%s", enable_query_rewriter, domain, queries, generated_title)

    session_title = generated_title or request.sessionTitle
    if not session_title and session_data:
        session_title = session_data.get("title")
    if not session_title:
        session_title = "Cuộc trò chuyện mới"

    enable_reranker = PIPELINE_CONFIG.get("reranking", "none") != "none"

    # Semantic Caching
    query_vector = None
    cached_response = None
    if ENABLE_SEMANTIC_CACHE and domain != "chitchat":
        rewritten_query = queries[0] if queries else last_message
        embedding = _get_embedding()
        if embedding:
            try:
                query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)
                cached_response = await asyncio.to_thread(check_cache, query_vector, SEMANTIC_CACHE_THRESHOLD)
            except EmbeddingServiceError as e:
                logger.warning("Cache embedding failed: %s", e)
                raise
            except Exception as e:
                logger.warning("Cache check failed: %s", e)
                if "401" in str(e) or "Unauthorized" in str(e) or "Invalid token" in str(e):
                    raise ValueError("API Key HuggingFace không hợp lệ hoặc đã hết hạn.")

    return PreparedTurnContext(
        session_id=session_id,
        last_message=last_message,
        chat_history_str=chat_history_str,
        domain=domain,
        queries=queries,
        enable_reranker=enable_reranker,
        session_title=session_title,
        query_vector=query_vector,
        cached_response=cached_response,
    )


async def retrieve_turn_context(
    pipeline: RAGPipeline,
    last_message: str,
    domain: str,
    queries: List[str],
    category: Optional[str],
    enable_reranker: bool,
    timing: PipelineTimingCollector,
) -> Tuple[List[Document], str, List[Dict[str, Any]]]:
    """Thực hiện aretrieve và định dạng context cho frontend."""
    retrieved_docs, context_text = await pipeline.aretrieve(
        query=last_message,
        k=RETRIEVER_CANDIDATE_K,
        category=category,
        rerank_top_k=RETRIEVER_K,
        domain=domain,
        queries=queries,
        enable_reranker=enable_reranker,
        context_token_budget=CONTEXT_TOKEN_BUDGET,
    )

    with timing.stage("context_building"):
        frontend_context = pipeline.format_for_frontend(retrieved_docs)

    return retrieved_docs, context_text, frontend_context


async def finalize_turn(
    request: ChatRequest,
    session_id: str,
    last_message: str,
    raw_text: str,
    frontend_context: List[Dict[str, Any]],
    query_vector: Optional[List[float]],
    domain: str,
    retrieved_docs: List[Document],
    persist_turn_fn: Optional[Callable] = None,
    session_title: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Validate trích dẫn, lọc context, cập nhật cache, persist turn và kích hoạt memory summarization."""
    validation = validate_generated_citations(raw_text, frontend_context)
    if validation.invalid_citation_ids or validation.fallback_used:
        logger.warning(
            "Answer citation validation adjusted output: invalid=%s fallback=%s",
            list(validation.invalid_citation_ids),
            validation.fallback_used,
        )
    output_text = validation.text

    final_context = filter_cited_context(output_text, frontend_context, MAX_CITATIONS)

    # Cập nhật cache nếu câu trả lời hợp lệ
    if query_vector and domain != "chitchat" and "Hiện tại hệ thống chưa thể gọi mô hình" not in output_text:
        try:
            await asyncio.to_thread(
                update_cache,
                query_vector=query_vector,
                original_query=last_message,
                response_text=output_text,
                context_used=final_context,
                retrieved_doc_ids=[doc.metadata.get("id") for doc in retrieved_docs if doc.metadata.get("id")],
            )
        except Exception as e:
            logger.warning("Failed to update cache: %s", e)

    # Lưu trữ turn vào Postgres
    persist_handler = persist_turn_fn or persist_completed_turn
    try:
        await persist_handler(
            request,
            session_id,
            last_message,
            output_text,
            final_context,
            session_title=session_title,
        )
    except TypeError:
        await persist_handler(
            request,
            session_id,
            last_message,
            output_text,
            final_context,
        )

    # Tóm tắt bộ nhớ bất đồng bộ
    if CHAT_STORAGE_MODE == "postgres" and session_id != "unknown":
        asyncio.create_task(summarize_session(
            session_id,
            last_message,
            output_text,
        ))

    return output_text, final_context
