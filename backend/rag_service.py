"""
Backward-compatible module.
Logic thực tế đã được chuyển sang:
  - app/services/vectorstore.py (FAISS, embedding, knowledge base)
  - app/services/rag.py (retrieval, context building)
File này tồn tại để tránh import lỗi từ code cũ.
"""
from app.services.vectorstore import init_vector_db, get_vectorstore  # noqa: F401
from app.services.rag import (  # noqa: F401
    get_retriever,
    build_nested_context,
    format_docs_for_frontend,
)