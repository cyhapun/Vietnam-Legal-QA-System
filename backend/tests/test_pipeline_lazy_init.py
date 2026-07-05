import app.services.pipeline as pipeline_module


def test_get_pipeline_initializes_when_missing(monkeypatch):
    pipeline_module._pipeline = None

    def fake_init_pipeline():
        pipeline_module._pipeline = object()

    monkeypatch.setattr(pipeline_module, "init_pipeline", fake_init_pipeline)

    assert pipeline_module.get_pipeline() is pipeline_module._pipeline
