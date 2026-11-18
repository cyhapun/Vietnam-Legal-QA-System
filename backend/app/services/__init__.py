"""Business logic services for the VietLaw RAG backend.

Packages & core modules:
- chat_orchestrator.py: Shared sync/streaming turn orchestration
- pipeline.py: Retrieval, reranking, and context assembly orchestrator
- llm.py: Google AI Studio LLM client with multi-key/model fallback
- storage.py: PostgreSQL & Qdrant persistence layer
- semantic_cache.py: Profile-isolated Qdrant semantic cache
- memory_manager.py: Async rolling conversation summarizer
- answer_validation.py: Deterministic citation verification
- embedding/: Local BGE-M3, Gemini Cloud, and legacy adapters
- reranking/: Local Cross-Encoder, Jina Cloud Reranker v2, similarity, and no-op
- search/: Qdrant hybrid dense/sparse searcher and legacy FAISS fallback
- rewriting/: LLM query normalization, domain classification, and smart titles
- chunking/: Clause-level legal document chunker
- context_builder/: 2-level nested legal cross-reference context builder
"""
