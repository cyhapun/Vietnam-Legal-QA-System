"""
RAG Pipeline Orchestrator — Kết nối các module thành pipeline hoàn chỉnh.

Pipeline flow:
    Query → Search → Rerank → Context Build → (LLM)

Hỗ trợ config-driven assembly để dễ dàng thực hiện ablation study.
"""
import os
import json
import glob
import time
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy

from app.config import (
    FAISS_INDEX_PATH, JSON_DATA_PATH, TRACKING_FILE,
    EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_RETRIES,
    EMBEDDING_SLEEP_BETWEEN_BATCHES, EMBEDDING_RETRY_BASE_WAIT,
    EMBEDDING_PROVIDER, PIPELINE_CONFIG,
    RETRIEVER_CANDIDATE_K, RETRIEVER_K,
)
from app.services.knowledge_base import load_knowledge_base
from app.services.embedding import (
    BaseEmbedding,
    HuggingFaceEndpointEmbedding,
    OllamaEmbedding,
)
from app.services.chunking import ClauseChunker
from app.services.search import FAISSSearcher, BM25Searcher, HybridSearcher
from app.services.reranking import NoReranker, CrossEncoderReranker
from app.services.context_builder import NestedContextBuilder
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.pipeline")


class RAGPipeline:
    """Orchestrator — kết nối Search, Rerank, và Context Builder.

    Cho phép swap từng component độc lập để thực hiện ablation study.

    Ví dụ:
        # Baseline
        pipeline = RAGPipeline(searcher=faiss, reranker=no_reranker, context_builder=nested)

        # + Reranker
        pipeline = RAGPipeline(searcher=faiss, reranker=cross_encoder, context_builder=nested)
    """

    def __init__(self, searcher, reranker, context_builder):
        self.searcher = searcher
        self.reranker = reranker
        self.context_builder = context_builder

        logger.info(
            "RAGPipeline initialized: search=%s, reranker=%s, context=%s",
            searcher.strategy_name,
            reranker.strategy_name,
            context_builder.strategy_name,
        )

    def retrieve(
        self,
        query: str,
        k: int = RETRIEVER_CANDIDATE_K,
        rerank_top_k: Optional[int] = None,
        category: Optional[str] = None,
    ) -> Tuple[List[Document], str]:
        """Thực hiện full retrieval pipeline: Search → Rerank → Context Build.

        Args:
            query: Câu hỏi của người dùng.
            k: Number of candidate documents to retrieve before reranking.
            rerank_top_k: Number of documents kept after reranking (default = RETRIEVER_K).
            category: Lọc theo lĩnh vực luật.

        Returns:
            Tuple (documents, context_string).
        """
        final_k = rerank_top_k or RETRIEVER_K

        # Step 1: Search
        docs = self.searcher.search(query, k=k, category=category)
        logger.info("Search: %d documents retrieved", len(docs))

        # Step 2: Rerank
        docs = self.reranker.rerank(query, docs, top_k=final_k)
        logger.info("Rerank: %d documents after reranking", len(docs))

        # Step 3: Build context
        context = self.context_builder.build(docs)

        return docs, context

    async def aretrieve(
        self,
        query: str,
        k: int = RETRIEVER_CANDIDATE_K,
        rerank_top_k: Optional[int] = None,
        category: Optional[str] = None,
    ) -> Tuple[List[Document], str]:
        """Async version của retrieve — dùng trong FastAPI endpoint."""
        final_k = rerank_top_k or RETRIEVER_K

        # Step 1: Async Search
        docs = await self.searcher.asearch(query, k=k, category=category)
        logger.info("Search: %d documents retrieved", len(docs))

        # Step 2: Rerank (sync — thường nhanh)
        docs = self.reranker.rerank(query, docs, top_k=final_k)
        logger.info("Rerank: %d documents after reranking", len(docs))

        # Step 3: Build context
        context = self.context_builder.build(docs)

        return docs, context

    def format_for_frontend(self, docs: List[Document]) -> List[Dict[str, Any]]:
        """Delegate format cho context_builder."""
        return self.context_builder.format_for_frontend(docs)


# ---------------------------------------------------------------------------
# FACTORY: Khởi tạo pipeline từ config
# ---------------------------------------------------------------------------

# Module-level state
_embedding = None
_pipeline: Optional[RAGPipeline] = None
_faiss_vectorstore: Optional[FAISS] = None


def _get_embedding() -> BaseEmbedding:
    """Lazy init embedding model (singleton)."""
    global _embedding
    if _embedding is None:
        if EMBEDDING_PROVIDER == "huggingface":
            _embedding = HuggingFaceEndpointEmbedding()
        elif EMBEDDING_PROVIDER == "ollama":
            _embedding = OllamaEmbedding()
        else:
            raise ValueError(
                f"Unknown embedding provider: {EMBEDDING_PROVIDER}"
            )
    return _embedding


def _get_processed_files() -> List[str]:
    """Đọc danh sách các file đã được embedding thành công trước đó."""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def _mark_file_as_processed(filename: str) -> None:
    """Đánh dấu file đã xử lý xong."""
    processed = _get_processed_files()
    if filename not in processed:
        processed.append(filename)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False, indent=4)


def _embed_single_file(file_path: str, chunker, embedding) -> None:
    """Nhúng (embedding) một file JSON vào FAISS index."""
    global _faiss_vectorstore

    filename = os.path.basename(file_path)
    logger.info("=" * 50)
    logger.info("BẮT ĐẦU EMBEDDING: %s", filename)
    logger.info("=" * 50)

    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # Dùng chunker module để tách documents
    splits = chunker.chunk(raw_data)
    logger.info("Số lượng chunk cần nhúng: %d", len(splits))

    lc_embeddings = embedding.langchain_embeddings

    for i in range(0, len(splits), EMBEDDING_BATCH_SIZE):
        batch = splits[i:i + EMBEDDING_BATCH_SIZE]
        logger.info("  + Đang đẩy batch %d → %d...", i, i + len(batch))

        for attempt in range(EMBEDDING_MAX_RETRIES):
            try:
                if _faiss_vectorstore is None:
                    _faiss_vectorstore = FAISS.from_documents(
                        batch, lc_embeddings,
                        distance_strategy=DistanceStrategy.COSINE
                    )
                else:
                    _faiss_vectorstore.add_documents(batch)

                time.sleep(EMBEDDING_SLEEP_BETWEEN_BATCHES)
                break

            except Exception as e:
                logger.warning(
                    "  -> Lỗi batch %d lần %d/%d: %s",
                    i, attempt + 1, EMBEDDING_MAX_RETRIES, str(e)[:100]
                )
                if attempt < EMBEDDING_MAX_RETRIES - 1:
                    wait_time = EMBEDDING_RETRY_BASE_WAIT * (attempt + 1)
                    logger.info("  -> Tạm nghỉ %ds...", wait_time)
                    time.sleep(wait_time)
                else:
                    logger.error("THẤT BẠI TẠI BATCH %d SAU %d LẦN THỬ.", i, EMBEDDING_MAX_RETRIES)
                    raise e

    _faiss_vectorstore.save_local(FAISS_INDEX_PATH)
    _mark_file_as_processed(filename)
    logger.info("ĐÃ HOÀN THÀNH VÀ LƯU FILE: %s", filename)


def _init_faiss_index(embedding) -> None:
    """Khởi tạo và cập nhật FAISS index."""
    global _faiss_vectorstore

    chunker = _create_chunker()
    lc_embeddings = embedding.langchain_embeddings

    processed_files = _get_processed_files()
    all_json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))
    pending_files = [f for f in all_json_files if os.path.basename(f) not in processed_files]

    # Tải index cũ nếu đã có
    if os.path.exists(FAISS_INDEX_PATH):
        logger.info("Đang tải FAISS Index từ ổ cứng...")
        _faiss_vectorstore = FAISS.load_local(
            FAISS_INDEX_PATH,
            lc_embeddings,
            allow_dangerous_deserialization=True
        )

    if not pending_files:
        logger.info("TẤT CẢ CÁC FILE ĐÃ ĐƯỢC EMBEDDING! Hệ thống sẵn sàng.")
        return

    logger.info("Còn %d file chưa được nhúng.", len(pending_files))
    _embed_single_file(pending_files[0], chunker, embedding)

    if len(pending_files) > 1:
        logger.info(
            "Còn %d file. Restart server để nhúng file tiếp theo.",
            len(pending_files) - 1
        )


def _create_chunker():
    """Tạo chunker dựa trên config."""
    strategy = PIPELINE_CONFIG.get("chunking", "clause")
    if strategy == "clause":
        return ClauseChunker()
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


def _create_searcher(embedding) -> Any:
    """Tạo searcher dựa trên config."""
    global _faiss_vectorstore

    strategy = PIPELINE_CONFIG.get("search", "faiss")

    # FAISS searcher luôn cần (dùng cho cả hybrid)
    if _faiss_vectorstore is None:
        raise RuntimeError("FAISS vectorstore chưa được khởi tạo!")

    faiss_searcher = FAISSSearcher(vectorstore=_faiss_vectorstore)

    if strategy == "faiss":
        return faiss_searcher

    elif strategy == "bm25":
        bm25_searcher = BM25Searcher()
        _build_bm25_index(bm25_searcher)
        return bm25_searcher

    elif strategy == "hybrid":
        bm25_searcher = BM25Searcher()
        _build_bm25_index(bm25_searcher)
        return HybridSearcher(
            vector_searcher=faiss_searcher,
            bm25_searcher=bm25_searcher,
            vector_weight=PIPELINE_CONFIG.get("hybrid_vector_weight", 0.5),
            bm25_weight=PIPELINE_CONFIG.get("hybrid_bm25_weight", 0.5),
        )

    else:
        raise ValueError(f"Unknown search strategy: {strategy}")


def _build_bm25_index(bm25_searcher: BM25Searcher) -> None:
    """Xây dựng BM25 index từ tất cả documents trong FAISS."""
    from app.services.knowledge_base import KNOWLEDGE_BASE, LAW_METADATA

    documents = []
    for clause_id, clause_data in KNOWLEDGE_BASE.items():
        law_id = clause_data.get("law_id")
        doc = Document(
            page_content=clause_data.get("content", ""),
            metadata={
                "id": clause_id,
                "law_id": law_id,
                "category": LAW_METADATA.get(law_id, {}).get(
                    "category",
                    "all",
                ),
            }
        )
        documents.append(doc)

    bm25_searcher.build_index(documents)


def _create_reranker():
    """Tạo reranker dựa trên config."""
    strategy = PIPELINE_CONFIG.get("reranking", "none")
    if strategy == "none":
        return NoReranker()
    elif strategy == "cross_encoder":
        model = PIPELINE_CONFIG.get("reranker_model", "BAAI/bge-reranker-v2-m3")
        return CrossEncoderReranker(model=model)
    else:
        raise ValueError(f"Unknown reranking strategy: {strategy}")


def _create_context_builder():
    """Tạo context builder dựa trên config."""
    strategy = PIPELINE_CONFIG.get("context_builder", "nested")
    if strategy == "nested":
        return NestedContextBuilder()
    else:
        raise ValueError(f"Unknown context_builder strategy: {strategy}")


# Cần import Any cho type hint
from typing import Any


def init_pipeline() -> None:
    """Khởi tạo toàn bộ pipeline: Knowledge Base → FAISS → Searcher → Pipeline.

    Gọi hàm này trong FastAPI startup event.
    """
    global _pipeline

    logger.info("=" * 60)
    logger.info("KHỞI TẠO RAG PIPELINE")
    logger.info("Config: %s", PIPELINE_CONFIG)
    logger.info("=" * 60)

    # 1. Nạp dữ liệu vào RAM
    load_knowledge_base()

    # 2. Khởi tạo embedding + FAISS index
    embedding = _get_embedding()
    _init_faiss_index(embedding)

    # 3. Tạo các components từ config
    searcher = _create_searcher(embedding)
    reranker = _create_reranker()
    context_builder = _create_context_builder()

    # 4. Assemble pipeline
    _pipeline = RAGPipeline(
        searcher=searcher,
        reranker=reranker,
        context_builder=context_builder,
    )

    logger.info("RAG Pipeline đã sẵn sàng!")


def get_pipeline() -> RAGPipeline:
    """Trả về pipeline hiện tại. Raise nếu chưa init."""
    if _pipeline is None:
        raise RuntimeError(
            "RAG Pipeline chưa được khởi tạo. "
            "Hãy gọi init_pipeline() trong startup event."
        )
    return _pipeline
