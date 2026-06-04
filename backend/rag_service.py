"""
Backward-compatible module.
Logic thực tế đã được chuyển sang:
  - app/services/knowledge_base.py (Knowledge Base, metadata)
  - app/services/embedding/ (Embedding strategies)
  - app/services/search/ (FAISS, BM25, Hybrid search)
  - app/services/pipeline.py (RAG Pipeline orchestrator)
File này tồn tại để tránh import lỗi từ code cũ.
"""
from app.services.pipeline import init_pipeline, get_pipeline  # noqa: F401