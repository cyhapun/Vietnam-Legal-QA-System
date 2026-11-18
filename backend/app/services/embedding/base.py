"""Protocol interface for text embedding providers."""
from typing import Protocol, List, runtime_checkable


@runtime_checkable
class BaseEmbedding(Protocol):
    """Common interface for swappable local and cloud embedding adapters."""

    @property
    def model_name(self) -> str:
        """Identifier used for logging and diagnostics."""
        ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of corpus passages for indexing."""
        ...

    def embed_query(self, text: str) -> List[float]:
        """Embed a single search query."""
        ...
