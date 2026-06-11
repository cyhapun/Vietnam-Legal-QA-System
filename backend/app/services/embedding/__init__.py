"""
Embedding Module — Abstract interface và implementations cho text embedding.

Protocol:
    BaseEmbedding: Interface chung cho tất cả embedding strategies.

Implementations:
    - HuggingFaceEndpointEmbedding: Gọi HuggingFace Inference API (mặc định)
    - OllamaEmbedding: Chạy model local qua Ollama
"""
from app.services.embedding.base import BaseEmbedding
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.services.embedding.ollama import OllamaEmbedding

__all__ = [
    "BaseEmbedding",
    "HuggingFaceEndpointEmbedding",
    "OllamaEmbedding",
]
