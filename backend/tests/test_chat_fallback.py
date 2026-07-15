from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


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
    monkeypatch.setattr("app.api.chat.get_pipeline", lambda: DummyPipeline())
    monkeypatch.setattr("app.api.chat.get_llm", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("LLM unavailable")))
    monkeypatch.setattr("app.services.pipeline._get_embedding", lambda *args, **kwargs: None)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Câu hỏi mẫu"}],
                "model": "default",
                "category": "all",
            },
        )

    assert response.status_code == 503
    body = response.json()
    assert "dịch vụ suy luận" in body["detail"].lower()
