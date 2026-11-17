import asyncio
import pytest
from langchain_core.documents import Document

from app.config import RETRIEVER_CANDIDATE_K, RETRIEVER_K
from app.services.pipeline import RAGPipeline
from app.services.rewriting.base import RewriteResult
from app.services.rewriting.llm_rewriter import LLMRewriter


class _MockContextBuilder:
    strategy_name = "mock_context"

    def __init__(self, char_per_doc=400):
        self.char_per_doc = char_per_doc

    def build(self, docs):
        # Mỗi document tạo ra một chuỗi dài char_per_doc ký tự (~100 tokens)
        blocks = []
        for doc in docs:
            doc_id = doc.metadata.get("id", "doc")
            blocks.append(f"[CĂN CỨ ID: {doc_id}] " + ("x" * self.char_per_doc))
        return "\n\n".join(blocks)

    def format_for_frontend(self, docs):
        return [{"id": d.metadata.get("id")} for d in docs]


class _MockRewriter:
    strategy_name = "mock_rewriter"

    def __init__(self, domain="legal", queries=None, title=None):
        self.domain = domain
        self.queries = queries or ["cau hoi da viet lai"]
        self.title = title

    def rewrite(self, query, history=None):
        return self.domain, self.queries, self.title


class _MockSearcher:
    strategy_name = "mock_searcher"

    def __init__(self):
        self.last_k = None

    def search(self, query, k=RETRIEVER_CANDIDATE_K, category=None):
        self.last_k = k
        return [
            Document(page_content=f"nội dung {i}", metadata={"id": f"doc_{i}"})
            for i in range(k)
        ]

    async def asearch(self, queries, k=RETRIEVER_CANDIDATE_K, category=None):
        self.last_k = k
        return [
            Document(page_content=f"nội dung {i}", metadata={"id": f"doc_{i}"})
            for i in range(k)
        ]


class _MockReranker:
    strategy_name = "mock_reranker"

    def rerank(self, query, documents, top_k=RETRIEVER_K):
        # Gán rank_score giảm dần và trả về top_k
        ranked = []
        for idx, doc in enumerate(documents):
            d = Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "rerank_score": 1.0 - (idx * 0.05)},
            )
            ranked.append(d)
        return ranked[:top_k]


def test_rewrite_result_schema_supports_smart_title():
    res = RewriteResult(
        domain="legal",
        queries=["thủ tục mua đất"],
        title="Thủ tục mua đất",
    )
    assert res.domain == "legal"
    assert res.queries == ["thủ tục mua đất"]
    assert res.title == "Thủ tục mua đất"

    res_no_title = RewriteResult(domain="chitchat", queries=[])
    assert res_no_title.title is None


def test_llm_rewriter_fallback_returns_safe_tuple():
    rewriter = LLMRewriter()
    # Mock chain.invoke raise Exception để kiểm tra robust fallback
    rewriter.chain = None
    domain, queries, title = rewriter.rewrite("câu hỏi lỗi")
    assert domain == "legal"
    assert queries == ["câu hỏi lỗi"]
    assert title is None


def test_retrieval_defaults_to_fixed_twenty_candidates():
    searcher = _MockSearcher()
    pipeline = RAGPipeline(
        rewriter=_MockRewriter(),
        searcher=searcher,
        reranker=_MockReranker(),
        context_builder=_MockContextBuilder(),
    )

    docs, _ = pipeline.retrieve("thủ tục hành chính")
    assert searcher.last_k == 20
    assert len(docs) == 5  # Reranked Top 5


def test_async_retrieval_defaults_to_fixed_twenty_candidates():
    searcher = _MockSearcher()
    pipeline = RAGPipeline(
        rewriter=_MockRewriter(),
        searcher=searcher,
        reranker=_MockReranker(),
        context_builder=_MockContextBuilder(),
    )

    docs, _ = asyncio.run(pipeline.aretrieve("thủ tục hành chính"))
    assert searcher.last_k == 20
    assert len(docs) == 5


def test_tail_chunk_pruning_keeps_all_when_within_budget():
    builder = _MockContextBuilder(char_per_doc=200)  # ~50 tokens mỗi doc
    pipeline = RAGPipeline(
        rewriter=_MockRewriter(),
        searcher=_MockSearcher(),
        reranker=_MockReranker(),
        context_builder=builder,
    )

    docs = [
        Document(page_content="doc 1", metadata={"id": "doc_1"}),
        Document(page_content="doc 2", metadata={"id": "doc_2"}),
        Document(page_content="doc 3", metadata={"id": "doc_3"}),
    ]

    # Ngân sách 1000 tokens dư dả cho 3 docs (~150 tokens)
    selected, context = pipeline._build_context_with_budget(docs, token_budget=1000)
    assert len(selected) == 3
    assert [d.metadata["id"] for d in selected] == ["doc_1", "doc_2", "doc_3"]
    assert "[CĂN CỨ ID: doc_1]" in context
    assert "[CĂN CỨ ID: doc_3]" in context


def test_tail_chunk_pruning_drops_lowest_ranked_chunks_first():
    # Mỗi doc khoảng 400 ký tự (~100 tokens)
    builder = _MockContextBuilder(char_per_doc=400)
    pipeline = RAGPipeline(
        rewriter=_MockRewriter(),
        searcher=_MockSearcher(),
        reranker=_MockReranker(),
        context_builder=builder,
    )

    # 4 documents theo thứ tự xếp hạng từ cao xuống thấp
    docs = [
        Document(page_content="doc 1", metadata={"id": "rank_1"}),
        Document(page_content="doc 2", metadata={"id": "rank_2"}),
        Document(page_content="doc 3", metadata={"id": "rank_3"}),
        Document(page_content="doc 4", metadata={"id": "rank_4"}),
    ]

    # Ngân sách 220 tokens: Chỉ đủ cho 2 docs (~200 tokens)
    selected, context = pipeline._build_context_with_budget(docs, token_budget=220)

    # Đảm bảo giữ lại rank 1 và rank 2, loại bỏ rank 4 rồi rank 3
    assert len(selected) == 2
    assert [d.metadata["id"] for d in selected] == ["rank_1", "rank_2"]
    assert "[CĂN CỨ ID: rank_1]" in context
    assert "[CĂN CỨ ID: rank_2]" in context
    assert "rank_3" not in context
    assert "rank_4" not in context


def test_tail_chunk_pruning_never_drops_rank_one_doc():
    builder = _MockContextBuilder(char_per_doc=1000)  # ~250 tokens
    pipeline = RAGPipeline(
        rewriter=_MockRewriter(),
        searcher=_MockSearcher(),
        reranker=_MockReranker(),
        context_builder=builder,
    )

    docs = [
        Document(page_content="doc 1", metadata={"id": "rank_1"}),
        Document(page_content="doc 2", metadata={"id": "rank_2"}),
    ]

    # Ngân sách cực nhỏ (50 tokens)
    selected, context = pipeline._build_context_with_budget(docs, token_budget=50)

    # Luôn giữ lại tối thiểu tài liệu Rank 1 quan trọng nhất
    assert len(selected) == 1
    assert selected[0].metadata["id"] == "rank_1"
    assert "[CĂN CỨ ID: rank_1]" in context
