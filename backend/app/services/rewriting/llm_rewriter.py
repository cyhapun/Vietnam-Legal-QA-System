import json
from typing import List, Optional, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
import logging

from app.config import PIPELINE_CONFIG
from .base import BaseRewriter, RewriteResult
from app.services.provider_registry import REWRITER_ROLE

logger = logging.getLogger(__name__)

class LLMRewriter(BaseRewriter):
    """
    LLM-based Query Rewriter that classifies queries into domains
    and translates slang/informal terms into formal legal terminology.
    """
    def __init__(self):
        from app.services.llm import get_llm
        self.llm = get_llm(role=REWRITER_ROLE)
        self.parser = JsonOutputParser(pydantic_object=RewriteResult)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Vietnamese legal query analyzer.
Your task is to analyze user queries and format them for a legal vector search engine.
1. Determine if the query is 'legal' (asking about laws, procedures, penalties) or 'chitchat' (greetings, off-topic).
2. Read the Conversation History (if provided) to understand the context. Then rewrite the Current User Query into a standalone, formal Vietnamese legal query. Resolve any pronouns or implicit references using the history.
3. Translate informal terms/slang into formal legal terminology.
4. Provide the formal standalone translation, and optionally 1-2 decomposed sub-queries if the question is complex.
5. If the Conversation History is empty or this is the first turn, generate a concise Vietnamese title (3-6 words) summarizing the core topic (e.g. "Điều kiện chuyển nhượng đất", "Thủ tục cấp sổ đỏ", "Xử phạt nồng độ cồn"). If NOT the first turn or history exists, title MUST be null.

You MUST respond strictly in the following JSON format:
{{
  "domain": "legal" or "chitchat",
  "queries": ["formal standalone translation", "sub-query (optional)"],
  "title": "Concise Vietnamese title" or null
}}

Do not output any other text or markdown block outside the JSON."""),
            ("human", "Conversation History (for context):\n{history}\n\nCurrent User Query: {query}")
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def _init_llm(self, provider: str = None, model_name: str = None):
        from app.services.llm import get_llm
        return get_llm(role=REWRITER_ROLE)

    def rewrite(self, query: str, history: str = None, runtime_config=None) -> Tuple[str, List[str], Optional[str]]:
        try:
            chain = self.chain
            if runtime_config is not None:
                from app.services.llm import get_llm
                chain = self.prompt | get_llm(
                    runtime_config=runtime_config,
                    role=REWRITER_ROLE,
                ) | self.parser

            result = chain.invoke({
                "query": query,
                "history": history if history else "No previous history."
            })
            domain = result.get("domain", "legal").lower()
            queries = result.get("queries", [])
            raw_title = result.get("title")
            title = None
            if raw_title and isinstance(raw_title, str):
                cleaned = raw_title.strip().strip('"').strip("'")
                if cleaned and cleaned.lower() not in ("null", "none"):
                    title = cleaned
            
            if not queries and domain == "legal":
                queries = [query]
                
            return domain, queries, title
            
        except OutputParserException as e:
            logger.error(f"Failed to parse JSON from LLM: {e}")
            # Robust fallback on parsing failure
            return "legal", [query], None
        except Exception as e:
            logger.error(f"Rewriting failed with error: {e}")
            return "legal", [query], None
