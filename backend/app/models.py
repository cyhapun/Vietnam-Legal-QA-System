"""
Pydantic models cho API request/response.
Tách riêng để dễ tái sử dụng và test.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.provider_registry import (
    INFERENCE_ROLES,
    PROVIDER_REGISTRY,
    is_supported_model,
    is_supported_provider,
    normalize_provider_id,
)


class Message(BaseModel):
    """Một tin nhắn trong lịch sử chat."""
    role: str
    content: str


class RuntimeProviderCredential(BaseModel):
    """Browser-provided provider credential for the current request."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_key: Optional[str] = Field(default=None, alias="apiKey")


class RuntimeProviderCredentials(BaseModel):
    """Provider credentials sent from browser storage per request."""

    model_config = ConfigDict(extra="forbid")

    google: Optional[RuntimeProviderCredential] = None
    huggingface: Optional[RuntimeProviderCredential] = None

    def get_api_key(self, provider: str) -> str:
        provider_id = normalize_provider_id(provider)
        credential = getattr(self, provider_id, None)
        return (credential.api_key or "").strip() if credential else ""


class RuntimeInferenceRole(BaseModel):
    """Provider/model assignment for one inference role."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str

    @model_validator(mode="after")
    def validate_provider_and_model(self):
        provider_id = normalize_provider_id(self.provider)
        self.provider = provider_id
        self.model = self.model.strip()

        if not is_supported_provider(provider_id):
            supported = ", ".join(sorted(PROVIDER_REGISTRY))
            raise ValueError(f"Unsupported inference provider '{provider_id}'. Supported providers: {supported}")

        if not is_supported_model(provider_id, self.model):
            raise ValueError(f"Unsupported model '{self.model}' for provider '{provider_id}'")

        return self


class RuntimeInferenceRoles(BaseModel):
    """Runtime model assignments for supported inference roles."""

    model_config = ConfigDict(extra="forbid")

    answer: Optional[RuntimeInferenceRole] = None
    rewriter: Optional[RuntimeInferenceRole] = None
    summarizer: Optional[RuntimeInferenceRole] = None

    def get(self, role: str) -> Optional[RuntimeInferenceRole]:
        role_id = role.strip().lower()
        if role_id not in INFERENCE_ROLES:
            return None
        return getattr(self, role_id)


class RuntimeInferenceConfig(BaseModel):
    """Legacy per-request inference override schema retained for internal/test compatibility."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    credentials: RuntimeProviderCredentials = Field(default_factory=RuntimeProviderCredentials)
    roles: RuntimeInferenceRoles = Field(default_factory=RuntimeInferenceRoles)
    use_server_fallbacks: bool = Field(default=True, alias="useServerFallbacks")

    def api_key_for(self, provider: str) -> str:
        return self.credentials.get_api_key(provider)


class ChatRequest(BaseModel):
    """Incoming chat payload from the frontend proxy."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    messages: List[Message]
    model: Optional[str] = "gemini-3.1-flash-lite"
    sessionId: Optional[str] = "unknown"
    sessionTitle: Optional[str] = "Cuộc trò chuyện mới"
    messageId: Optional[str] = None
    category: str = "all"  # Law code filter (or 'all')
    streaming: bool = True


class ChatResponse(BaseModel):
    """Non-streaming chat response payload."""
    text: str
    contextUsed: List[Dict[str, Any]]
