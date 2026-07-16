from fastapi.testclient import TestClient

import app.main as main_module


def _app_without_startup_side_effects(monkeypatch):
    monkeypatch.setattr(main_module, "load_knowledge_base", lambda: None)
    monkeypatch.setattr(main_module, "initialize_storage", lambda: None)
    monkeypatch.setattr(main_module, "init_pipeline", lambda: None)
    return main_module.create_app()


def test_health_is_fast_and_does_not_call_dependencies(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch)

    def fail_if_called():
        raise AssertionError("readiness dependency should not be called by /health")

    monkeypatch.setattr(main_module, "_check_artifacts", fail_if_called)
    monkeypatch.setattr(main_module, "_check_postgres", fail_if_called)
    monkeypatch.setattr(main_module, "_check_qdrant", fail_if_called)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_success_with_mocked_dependencies(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch)
    monkeypatch.setattr(
        main_module,
        "_check_artifacts",
        lambda: {
            "embedding": {"status": "ok", "configured": True, "weights": True},
            "reranker": {"status": "ok", "enabled": True, "weights": True},
        },
    )
    monkeypatch.setattr(
        main_module,
        "_check_postgres",
        lambda: {"status": "ok", "host": "localhost", "port": 15432, "database": "vietlaw"},
    )
    monkeypatch.setattr(
        main_module,
        "_check_qdrant",
        lambda: {
            "status": "ok",
            "host": "qdrant.example",
            "collection": "vietlaw_clauses",
            "points": 5756,
            "denseVector": {"name": "text-dense", "dimension": 1024, "distance": "Cosine"},
        },
    )

    with TestClient(app) as client:
        response = client.get("/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["components"]["embedding"]["status"] == "ok"
    assert body["components"]["qdrant"]["denseVector"]["dimension"] == 1024


def test_readiness_returns_503_when_required_dependency_fails(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch)
    monkeypatch.setattr(
        main_module,
        "_check_artifacts",
        lambda: {
            "embedding": {"status": "ok", "configured": True, "weights": True},
            "reranker": {"status": "ok", "enabled": True, "weights": True},
        },
    )
    monkeypatch.setattr(main_module, "_check_postgres", lambda: {"status": "ok"})

    def qdrant_down():
        raise RuntimeError("missing collection")

    monkeypatch.setattr(main_module, "_check_qdrant", qdrant_down)

    with TestClient(app) as client:
        response = client.get("/readiness")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "not_ready"
    assert detail["components"]["qdrant"]["status"] == "error"
