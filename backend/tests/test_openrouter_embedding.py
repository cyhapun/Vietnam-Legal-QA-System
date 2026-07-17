import json

from app.services.embedding.hf_endpoint import OpenRouterEmbeddingClient


def test_openrouter_embedding_client_orders_vectors_by_index(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "data": [
                        {"index": 1, "embedding": [0.0, 1.0]},
                        {"index": 0, "embedding": [1.0, 0.0]},
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.embedding.hf_endpoint.request.urlopen", fake_urlopen)

    client = OpenRouterEmbeddingClient(
        api_key="token",
        model="baai/bge-m3",
        base_url="https://openrouter.ai/api/v1",
    )

    assert client.embed(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
