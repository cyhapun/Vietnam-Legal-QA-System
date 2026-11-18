"""Embedding adapters for local fine-tuned and cloud RAG profiles.

Implementations:
    - HuggingFaceEndpointEmbedding: Local fine-tuned BGE-M3 or HF Inference API
    - GeminiEmbedding: Google AI Studio gemini-embedding-001 (1024-dim, cloud default)
    - OllamaEmbedding: Legacy local Ollama adapter
"""
from typing import Optional
from app.services.embedding.base import BaseEmbedding
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.services.embedding.gemini import GeminiEmbedding
from app.services.embedding.ollama import OllamaEmbedding
from app.services.embedding.fallback import FallbackEmbedding


def get_embedding(api_key: Optional[str] = None) -> BaseEmbedding:
    """Factory khởi tạo embedding adapter dựa trên EMBEDDING_PROVIDER trong config."""
    from app.config import EMBEDDING_PROVIDER
    if EMBEDDING_PROVIDER == "gemini":
        return GeminiEmbedding()
    elif EMBEDDING_PROVIDER == "ollama":
        return OllamaEmbedding()
    return HuggingFaceEndpointEmbedding(api_key=api_key)


__all__ = [
    "BaseEmbedding",
    "HuggingFaceEndpointEmbedding",
    "GeminiEmbedding",
    "OllamaEmbedding",
    "FallbackEmbedding",
    "get_embedding",
]
