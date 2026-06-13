"""
FAISS Search — Vector similarity search dùng FAISS index.
Đây là implementation mặc định, giữ nguyên logic từ rag.py cũ.
"""
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from app.config import RETRIEVER_K, RETRIEVER_FETCH_K, RETRIEVER_LAMBDA_MULT
from app.services.knowledge_base import (
    ALL_LAWS_CATEGORY,
    document_matches_category,
    normalize_category,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.search.faiss")


class FAISSSearcher:
    """Vector similarity search dùng FAISS.

    Sử dụng MMR (Maximal Marginal Relevance) để cân bằng
    giữa relevance và diversity trong kết quả.
    """

    def __init__(
        self,
        vectorstore: FAISS,
        fetch_k: int = RETRIEVER_FETCH_K,
        lambda_mult: float = RETRIEVER_LAMBDA_MULT,
    ):
        self._vectorstore = vectorstore
        self._fetch_k = fetch_k
        self._lambda_mult = lambda_mult

    @property
    def strategy_name(self) -> str:
        return "faiss_mmr"

    @property
    def vectorstore(self) -> FAISS:
        """Trả về FAISS vectorstore — cần cho indexing."""
        return self._vectorstore

    def search(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Tìm kiếm bằng MMR trên FAISS index."""
        search_kwargs = {
            "k": k,
            "fetch_k": max(self._fetch_k, k),
            "lambda_mult": self._lambda_mult,
        }

        normalized_category = normalize_category(category)
        if normalized_category != ALL_LAWS_CATEGORY:
            search_kwargs["filter"] = (
                lambda metadata: document_matches_category(
                    metadata,
                    normalized_category,
                )
            )

        retriever = self._vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs,
        )
        return retriever.invoke(query)

    async def asearch(
        self,
        query: str,
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Async version — dùng trong FastAPI endpoint."""
        search_kwargs = {
            "k": k,
            "fetch_k": max(self._fetch_k, k),
            "lambda_mult": self._lambda_mult,
        }

        normalized_category = normalize_category(category)
        if normalized_category != ALL_LAWS_CATEGORY:
            search_kwargs["filter"] = (
                lambda metadata: document_matches_category(
                    metadata,
                    normalized_category,
                )
            )

        retriever = self._vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs,
        )
        return await retriever.ainvoke(query)
