from typing import List, Tuple
from .base import BaseRewriter

class NoOpRewriter(BaseRewriter):
    """
    A simple rewriter that does not alter the query. 
    Useful as a fallback or for ablation studies.
    """
    def rewrite(self, query: str) -> Tuple[str, List[str]]:
        return "legal", [query]
