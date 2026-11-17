import pytest
import app.services.llm as llm_module


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
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "google-token-1")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEYS", "google-token-1")
    monkeypatch.setattr(llm_module, "GOOGLE_FALLBACK_MODELS", "")
    monkeypatch.setattr(
        llm_module,
        "GOOGLE_OPENAI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def test_google_model_detection():
    assert llm_module.is_google_chat_model("gemini-3.1-flash-lite")
    assert llm_module.is_google_chat_model("gemini-2.5-flash-lite")
    assert llm_module.is_google_chat_model("gemini-2.5-flash")
    assert not llm_module.is_google_chat_model("google/gemma-4-31B-it")
    assert not llm_module.is_google_chat_model("qwen2.5:7b-instruct")


def test_parse_google_api_keys(monkeypatch):
    # Single key
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEYS", "key1")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "")
    assert llm_module.parse_google_api_keys() == ["key1"]

    # Comma-separated with whitespace and duplicates
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEYS", " key1 , key2, key1 , key3 ")
    assert llm_module.parse_google_api_keys() == ["key1", "key2", "key3"]

    # Explicit key override
    assert llm_module.parse_google_api_keys("explicit_key") == ["explicit_key"]


def test_parse_google_fallback_models(monkeypatch):
    monkeypatch.setattr(
        llm_module,
        "GOOGLE_FALLBACK_MODELS",
        "gemini-3.1-flash-lite, gemini-2.5-flash-lite, invalid-model, gemini-2.5-flash",
    )
    # primary_model = "gemini-3.1-flash-lite" -> should be excluded from fallbacks
    fallbacks = llm_module.parse_google_fallback_models("gemini-3.1-flash-lite")
    assert fallbacks == ["gemini-2.5-flash-lite", "gemini-2.5-flash"]


def test_selected_google_model_uses_google_endpoint(monkeypatch):
    _patch_chat_factory(monkeypatch)

    llm = llm_module.get_llm("gemini-3.1-flash-lite")

    assert llm.model == "gemini-3.1-flash-lite"
    assert llm.api_key == "google-token-1"
    assert llm.base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert llm.fallbacks == []


def test_multi_key_key_first_fallback_order(monkeypatch):
    """
    Xác minh thứ tự ưu tiên đổi Key trước:
    (Model_A, Key_1) -> (Model_A, Key_2) -> (Model_B, Key_1) -> (Model_B, Key_2)
    """
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEYS", "key1,key2")
    monkeypatch.setattr(llm_module, "GOOGLE_FALLBACK_MODELS", "gemini-2.5-flash-lite")

    llm = llm_module.get_llm("gemini-3.1-flash-lite")

    # Primary: Model A, Key 1
    assert llm.model == "gemini-3.1-flash-lite"
    assert llm.api_key == "key1"

    # Fallbacks chain:
    # 1. Model A, Key 2
    # 2. Model B, Key 1
    # 3. Model B, Key 2
    expected = [
        ("gemini-3.1-flash-lite", "key2"),
        ("gemini-2.5-flash-lite", "key1"),
        ("gemini-2.5-flash-lite", "key2"),
    ]
    actual = [(f.model, f.api_key) for f in llm.fallbacks]
    assert actual == expected


def test_missing_google_key_raises_runtime_error(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEYS", "")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEYS", raising=False)

    with pytest.raises(RuntimeError, match="Không có Google API Key"):
        llm_module.get_llm("gemini-3.1-flash-lite")


def test_unsupported_google_model_raises_clear_error(monkeypatch):
    _patch_chat_factory(monkeypatch)

    with pytest.raises(ValueError, match="Unsupported Google model"):
        llm_module.get_llm("unsupported-google-model")


def test_duplicate_google_fallback_model_is_not_retried(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "GOOGLE_FALLBACK_MODELS", "gemini-3.1-flash-lite")

    llm = llm_module.get_llm("gemini-3.1-flash-lite")

    assert llm.fallbacks == []
