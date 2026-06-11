import sys
import types
import unittest
from unittest.mock import patch


try:
    from langchain_core.documents import Document as _Document
except ModuleNotFoundError:
    langchain_core = types.ModuleType("langchain_core")
    documents_module = types.ModuleType("langchain_core.documents")

    class _Document:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    documents_module.Document = _Document
    langchain_core.documents = documents_module
    sys.modules["langchain_core"] = langchain_core
    sys.modules["langchain_core.documents"] = documents_module

try:
    import dotenv as _dotenv
except ModuleNotFoundError:
    dotenv_module = types.ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv_module

import app.services.chunking.clause_chunker as clause_chunker_module
from app.services.chunking.sub_clause_splitter import split_long_clause

ClauseChunker = clause_chunker_module.ClauseChunker


class SubClauseSplitterTests(unittest.TestCase):
    def test_short_chunk_is_not_split(self):
        content = "Khoản ngắn giữ nguyên nội dung."

        self.assertEqual(split_long_clause(content), [content])

    def test_long_chunk_with_lettered_points_is_split(self):
        introduction = " ".join(["mở đầu"] * 10)
        point_a = "a) " + " ".join(["nội dung a"] * 100)
        point_b = "b) " + " ".join(["nội dung b"] * 100)
        point_c = "c) " + " ".join(["nội dung c"] * 100)
        content = "\n".join([introduction, point_a, point_b, point_c])

        parts = split_long_clause(content)

        self.assertEqual(len(parts), 3)
        self.assertTrue(parts[0].startswith(introduction))
        self.assertIn("\na)", parts[0])
        self.assertTrue(parts[1].startswith("b)"))
        self.assertTrue(parts[2].startswith("c)"))


class ClauseChunkerTests(unittest.TestCase):
    def test_embedding_prefix_uses_law_and_article_metadata(self):
        raw_data = {
            "law_info": {
                "law_id": "LAW_1",
                "law_name": "Luật Kiểm thử",
            },
            "clauses": [
                {
                    "id": "LAW_1_D5_K1",
                    "position": {
                        "article": "5",
                        "article_title": "Nguyên tắc áp dụng",
                        "clause": 1,
                    },
                    "content": "Nội dung khoản.",
                }
            ],
        }

        with patch.object(clause_chunker_module.logger, "info"):
            documents = ClauseChunker().chunk(raw_data)

        self.assertEqual(len(documents), 1)
        self.assertEqual(
            documents[0].page_content,
            "Luật Kiểm thử - Điều 5 Nguyên tắc áp dụng: Nội dung khoản.",
        )
        self.assertEqual(
            documents[0].metadata,
            {
                "id": "LAW_1_D5_K1",
                "law_id": "LAW_1",
                "category": "Khác",
                "chunk_part": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
