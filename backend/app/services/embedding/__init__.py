"""
Embedding Module — Abstract interface và implementations cho text embedding.

Protocol:
    BaseEmbedding: Interface chung cho tất cả embedding strategies.

Implementations:
    - HuggingFaceEndpointEmbedding: Gọi HuggingFace Inference API (mặc định)
    - (Future) LocalEmbedding: Chạy model trên máy local
"""
from app.services.embedding.base import BaseEmbedding
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding

__all__ = ["BaseEmbedding", "HuggingFaceEndpointEmbedding"]
