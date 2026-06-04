"""
Clause Chunker — Mỗi điều khoản (clause) là một chunk.
Đây là strategy mặc định, giữ nguyên logic từ vectorstore.py cũ.
"""
from typing import List, Dict, Any

from langchain_core.documents import Document

from app.services.knowledge_base import determine_category
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.chunking.clause")


class ClauseChunker:
    """Chunking theo đơn vị điều khoản (Khoản).

    Mỗi clause trong file JSON trở thành một Document riêng biệt.
    Đây là cách tiếp cận tự nhiên nhất cho văn bản pháp luật Việt Nam
    vì mỗi khoản thường chứa một ý pháp lý hoàn chỉnh.
    """

    @property
    def strategy_name(self) -> str:
        return "clause"

    def chunk(self, raw_data: Dict[str, Any]) -> List[Document]:
        """Tách từng clause thành 1 Document.

        Args:
            raw_data: Dữ liệu JSON chứa 'law_info' và 'clauses'.

        Returns:
            Danh sách Document với metadata gồm id, law_id, category.
        """
        law_info = raw_data.get("law_info", {})
        law_id = law_info.get("law_id")
        law_name = law_info.get("law_name", "")
        category = determine_category(law_name)

        documents = []
        for clause in raw_data.get("clauses", []):
            content = clause.get("content", "")
            if not content.strip():
                continue

            metadata = {
                "id": clause["id"],
                "law_id": law_id,
                "category": category,
            }
            documents.append(
                Document(page_content=content, metadata=metadata)
            )

        logger.info(
            "Chunked '%s' → %d documents (strategy: clause)",
            law_name[:50], len(documents)
        )
        return documents
