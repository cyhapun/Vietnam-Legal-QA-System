import json
from typing import List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
import logging

from app.config import PIPELINE_CONFIG
from .base import BaseRewriter, RewriteResult

logger = logging.getLogger(__name__)

class LLMRewriter(BaseRewriter):
    """
    LLM-based Query Rewriter that classifies queries into domains
    and translates slang/informal terms into formal legal terminology.
    """
    def __init__(self):
        provider = PIPELINE_CONFIG.get("rewriter_model_provider", "ollama")
        model_name = PIPELINE_CONFIG.get("rewriter_model_name", "qwen2.5:1.5b")
        
        self.llm = self._init_llm(provider, model_name)
        
        self.parser = JsonOutputParser(pydantic_object=RewriteResult)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Vietnamese legal query analyzer.
Your task is to analyze user queries and format them for a legal vector search engine.
1. Determine if the query is 'legal' (asking about laws, procedures, penalties) or 'chitchat' (greetings, off-topic).
2. If 'legal', rewrite the query by translating informal terms/slang (e.g., "sổ đỏ" -> "giấy chứng nhận quyền sử dụng đất", "làm giấy tờ xe" -> "đăng ký xe") into formal Vietnamese legal terminology.
3. Provide the original query, the formal translation, and optionally 1-2 decomposed sub-queries if the question is complex.

You MUST respond strictly in the following JSON format:
{{
  "domain": "legal" or "chitchat",
  "queries": ["original query", "formal translation", "sub-query (optional)"]
}}

Do not output any other text or markdown block outside the JSON."""),
            ("human", "User Query: {query}")
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def _init_llm(self, provider: str, model_name: str):
        if provider == "huggingface":
            from app.services.llm import get_llm
            return get_llm(model_name)
        elif provider == "ollama":
            try:
                from langchain_community.chat_models import ChatOllama
                from app.config import OLLAMA_BASE_URL
                return ChatOllama(model=model_name, base_url=OLLAMA_BASE_URL, temperature=0.1)
            except ImportError:
                logger.warning("Could not import ChatOllama, falling back to HuggingFace")
                from app.services.llm import get_llm
                return get_llm(model_name)
        else:
            from app.services.llm import get_llm
            return get_llm(model_name)

    def rewrite(self, query: str) -> Tuple[str, List[str]]:
        try:
            result = self.chain.invoke({"query": query})
            domain = result.get("domain", "legal").lower()
            queries = result.get("queries", [])
            
            if not queries and domain == "legal":
                queries = [query]
                
            return domain, queries
            
        except OutputParserException as e:
            logger.error(f"Failed to parse JSON from LLM: {e}")
            # Robust fallback on parsing failure
            return "legal", [query]
        except Exception as e:
            logger.error(f"Rewriting failed with error: {e}")
            return "legal", [query]
