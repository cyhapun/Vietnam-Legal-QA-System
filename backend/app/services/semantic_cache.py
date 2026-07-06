"""
Semantic Caching Service
"""
import uuid
import time
from typing import Optional, Dict, Any, List

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    ENABLE_SEMANTIC_CACHE,
    SEMANTIC_CACHE_THRESHOLD
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.semantic_cache")

_qdrant_client = None

def _get_client() -> Optional[QdrantClient]:
    global _qdrant_client
    if _qdrant_client is None:
        try:
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        except Exception as e:
            logger.warning("Failed to initialize QdrantClient for semantic cache: %s", e)
    return _qdrant_client

def check_cache(query_vector: List[float]) -> Optional[Dict[str, Any]]:
    """
    Check if a similar query exists in the semantic cache.
    Returns the cached payload (including text and contextUsed) if found, else None.
    """
    if not ENABLE_SEMANTIC_CACHE:
        return None

    client = _get_client()
    if not client:
        return None

    try:
        try:
            # Try query_points (newer versions)
            search_result = client.query_points(
                collection_name="semantic_cache",
                query=query_vector,
                limit=1,
                score_threshold=SEMANTIC_CACHE_THRESHOLD
            ).points
        except AttributeError:
            # Fallback for older versions
            search_result = client.search(
                collection_name="semantic_cache",
                query_vector=query_vector,
                limit=1,
                score_threshold=SEMANTIC_CACHE_THRESHOLD
            )
        
        if search_result and len(search_result) > 0:
            hit = search_result[0]
            logger.info("Semantic cache HIT! Score: %.4f", hit.score)
            return hit.payload
        
        logger.info("Semantic cache MISS.")
        return None
        
    except Exception as e:
        logger.warning("Error checking semantic cache: %s", e)
        return None

def update_cache(query_vector: List[float], original_query: str, response_text: str, context_used: List[Dict[str, Any]]) -> None:
    """
    Update the semantic cache with a new query and its generated response.
    """
    if not ENABLE_SEMANTIC_CACHE:
        return

    client = _get_client()
    if not client:
        return

    try:
        point_id = str(uuid.uuid4())
        
        payload = {
            "original_query": original_query,
            "response_text": response_text,
            "context_used": context_used,
            "timestamp": time.time()
        }
        
        client.upsert(
            collection_name="semantic_cache",
            points=[
                qdrant_models.PointStruct(
                    id=point_id,
                    vector=query_vector,
                    payload=payload
                )
            ]
        )
        logger.info("Saved response to semantic cache (id: %s)", point_id)
        
    except Exception as e:
        logger.warning("Error updating semantic cache: %s", e)
