from types import SimpleNamespace

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.chat import chat_endpoint
import app.main as main_module
from app.models import ChatRequest


class DummyRewriter:
    def rewrite(self, query, history_str):
        return "all", [query]

class DummyPipeline:
    def __init__(self):
        self.rewriter = DummyRewriter()

    async def aretrieve(self, query, category=None, **kwargs):
        return [SimpleNamespace(page_content="Nội dung mẫu", metadata={"id": "1"})], "Tài liệu tham khảo"

    def format_for_frontend(self, docs):
        return [{"id": doc.metadata["id"]} for doc in docs]


def test_chat_returns_http_error_when_llm_is_unavailable(monkeypatch):
    async def immediate_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(main_module, "LOCAL_MODELS_PRELOAD_ENABLED", False)
    monkeypatch.setattr(main_module, "LOCAL_MODELS_WARMUP_ENABLED", False)
    monkeypatch.setattr(main_module, "load_knowledge_base", lambda: None)
    monkeypatch.setattr(main_module, "initialize_storage", lambda: None)
    monkeypatch.setattr(main_module, "init_pipeline", lambda: None)
    monkeypatch.setattr("app.api.chat.asyncio.to_thread", immediate_to_thread)
    monkeypatch.setattr("app.api.chat.get_pipeline", lambda: DummyPipeline())
    monkeypatch.setattr("app.api.chat.get_llm", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("LLM unavailable")))
    monkeypatch.setattr("app.services.pipeline._get_embedding", lambda *args, **kwargs: None)

    request = ChatRequest.model_validate({
        "messages": [{"role": "user", "content": "Câu hỏi mẫu"}],
        "model": "default",
        "category": "all",
        "enableMemory": False,
        "enableSemanticCache": False,
    })
    http_request = Request({"type": "http", "method": "POST", "path": "/chat", "headers": []})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(chat_endpoint(request, http_request))

    assert exc_info.value.status_code == 503
    assert "dịch vụ suy luận" in exc_info.value.detail.lower()
