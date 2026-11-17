import pytest
from pydantic import ValidationError

import app.services.llm as llm_module
from app.models import ChatRequest, RuntimeInferenceConfig
from app.services.provider_registry import redact_runtime_inference_config


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.model = kwargs["model"]
        self.base_url = kwargs["base_url"]
        self.api_key = kwargs["api_key"]
        self.fallbacks = []

    def with_fallbacks(self, fallbacks):
        self.fallbacks = fallbacks
        return self


def _patch_chat_factory(monkeypatch):
    monkeypatch.setattr(llm_module, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "env-google-token")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEYS", "env-google-token")


def _runtime_config(provider="google", model="gemini-3.1-flash-lite", key="runtime-google-token", role="answer"):
    return RuntimeInferenceConfig.model_validate({
        "credentials": {
            provider: {"apiKey": key}
        },
        "roles": {
            role: {"provider": provider, "model": model}
        },
        "useServerFallbacks": False,
    })


def test_runtime_inference_config_rejects_unsupported_provider():
    with pytest.raises(ValidationError):
        RuntimeInferenceConfig.model_validate({
            "roles": {
                "answer": {"provider": "custom", "model": "anything"}
            }
        })


def test_runtime_inference_config_rejects_arbitrary_base_url():
    with pytest.raises(ValidationError):
        RuntimeInferenceConfig.model_validate({
            "roles": {
                "answer": {
                    "provider": "google",
                    "model": "gemini-3.1-flash-lite",
                    "baseUrl": "http://169.254.169.254",
                }
            }
        })


def test_chat_request_ignores_runtime_pipeline_overrides():
    request = ChatRequest.model_validate({
        "messages": [{"role": "user", "content": "test"}],
        "candidateK": 20,
        "inferenceConfig": {
            "roles": {
                "answer": {"provider": "google", "model": "gemini-3.1-flash-lite"}
            }
        },
    })
    assert request.model == "gemini-3.1-flash-lite"
    assert not hasattr(request, "candidateK")
    assert not hasattr(request, "inferenceConfig")


def test_chat_request_defaults():
    request = ChatRequest.model_validate({
        "messages": [{"role": "user", "content": "test"}],
    })
    assert request.model == "gemini-3.1-flash-lite"
    assert request.category == "all"
    assert request.sessionId == "unknown"


def test_runtime_google_key_overrides_environment_key(monkeypatch):
    _patch_chat_factory(monkeypatch)
    config = _runtime_config()

    llm = llm_module.get_llm(
        "gemini-3.1-flash-lite",
        runtime_config=config,
        role="answer",
    )

    assert llm.model == "gemini-3.1-flash-lite"
    assert llm.api_key == "runtime-google-token"
    assert llm.fallbacks == []


def test_runtime_role_routing(monkeypatch):
    _patch_chat_factory(monkeypatch)
    config = RuntimeInferenceConfig.model_validate({
        "credentials": {
            "google": {"apiKey": "runtime-google-token"},
        },
        "roles": {
            "answer": {"provider": "google", "model": "gemini-3.1-flash-lite"},
            "rewriter": {"provider": "google", "model": "gemini-2.5-flash"},
            "summarizer": {"provider": "google", "model": "gemini-3.1-flash-lite"},
        },
        "useServerFallbacks": False,
    })

    answer = llm_module.get_llm("unused", runtime_config=config, role="answer")
    rewriter = llm_module.get_llm("unused", runtime_config=config, role="rewriter")
    summarizer = llm_module.get_llm("unused", runtime_config=config, role="summarizer")

    assert answer.model == "gemini-3.1-flash-lite"
    assert answer.api_key == "runtime-google-token"
    assert rewriter.model == "gemini-2.5-flash"
    assert rewriter.api_key == "runtime-google-token"
    assert summarizer.model == "gemini-3.1-flash-lite"


def test_missing_runtime_key_without_server_fallback_raises(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEYS", "")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEYS", raising=False)
    config = RuntimeInferenceConfig.model_validate({
        "roles": {
            "answer": {"provider": "google", "model": "gemini-3.1-flash-lite"}
        },
        "useServerFallbacks": False,
    })

    with pytest.raises(RuntimeError):
        llm_module.get_llm("gemini-3.1-flash-lite", runtime_config=config)


def test_redacts_runtime_api_keys():
    config = _runtime_config()

    redacted = redact_runtime_inference_config(config)

    assert redacted["credentials"]["google"]["apiKey"] == "<redacted>"
    assert "runtime-google-token" not in str(redacted)
