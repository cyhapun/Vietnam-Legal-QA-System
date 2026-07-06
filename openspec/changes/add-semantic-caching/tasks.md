## 1. Configuration Setup

- [ ] 1.1 Add `SEMANTIC_CACHE_THRESHOLD` (default 0.95) and `ENABLE_SEMANTIC_CACHE` (default true) to `.env.example`
- [ ] 1.2 Update `backend/app/config.py` to load and expose the new cache configuration variables

## 2. Storage Setup

- [ ] 2.1 Update Qdrant initialization logic (in `storage.py` or equivalent startup script) to create a `semantic_cache` collection if it does not exist
- [ ] 2.2 Ensure the `semantic_cache` collection uses the same vector dimension as the embedding model being used

## 3. Core Implementation

- [ ] 3.1 Create a new service `backend/app/services/semantic_cache.py`
- [ ] 3.2 Implement `check_cache(query_vector)` to search the `semantic_cache` collection with similarity threshold filtering
- [ ] 3.3 Implement `update_cache(query_vector, original_query, response_text, context_used)` to insert new records into Qdrant

## 4. Pipeline Integration

- [ ] 4.1 Update `backend/app/api/chat.py` to intercept the query after the rewriting phase
- [ ] 4.2 In `chat.py`, generate the embedding for the rewritten query and call `check_cache()`
- [ ] 4.3 If a cache hit occurs, format and return the cached `response_text` and `contextUsed`, bypassing the LLM
- [ ] 4.4 If a cache miss occurs, proceed with the normal pipeline and finally call `update_cache()` before returning the response

## 5. Maintenance Scripts (Optional but Recommended)

- [ ] 5.1 Create a script `backend/scripts/clear_semantic_cache.py` to flush the `semantic_cache` collection when the knowledge base is updated
