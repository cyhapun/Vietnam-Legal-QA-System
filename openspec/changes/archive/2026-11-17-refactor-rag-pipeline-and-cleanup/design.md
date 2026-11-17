# Design: Refactor RAG Pipeline & Codebase Cleanup

## Architectural Overview

Bản thiết kế này tập trung vào việc tinh gọn, khử trùng lặp và tối ưu hóa hiệu năng cho RAG Pipeline backend mà không làm thay đổi các giao diện API hiện hành đối với Frontend.

```
                           FastAPI Router (`api/chat.py`)
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
           `chat_endpoint`             `chat_stream_endpoint`
           (Non-streaming)                   (Streaming)
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                ┌─────────────────────────────────────┐
                │        RAG TURN ORCHESTRATOR        │
                │  (`services/chat_orchestrator.py`)  │
                └──────────────────┬──────────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
[1. PREPARE TURN]           [2. RETRIEVE]               [3. FINALIZE TURN]
- Build Session History     - `RAGPipeline.aretrieve`   - Validate `<cite id="...">`
- Query Rewrite & Routing   - Token Budget Truncate     - Update Semantic Cache
- Check Semantic Cache      - Format Frontend Context   - Persist Sequential Turn
                                                        - Summarize Session Async
```

---

## Detailed Components

### 1. Dọn dẹp Code chết: Loại bỏ `app/services/rag.py`
- **Nguyên nhân:** File `rag.py` ban đầu được tách từ monolith `rag_service.py` để chứa hàm FAISS và recursive nested context. Sau đó toàn bộ logic này đã được chuyển hóa thành các component độc lập:
  - `ClauseChunker` trong `services/chunking/`
  - `FAISSSearcher` trong `services/search/faiss_search.py`
  - `NestedContextBuilder` trong `services/context_builder/nested_context.py`
  - `RAGPipeline` trong `services/pipeline.py`
- **Hành động:** 
  - Xóa bỏ file `backend/app/services/rag.py`.
  - Kiểm tra toàn bộ tests và mã nguồn để khẳng định không có import dangling nào.

### 2. Thiết kế `RAGTurnOrchestrator` trong `backend/app/services/chat_orchestrator.py`
Thay vì để `api/chat.py` tự thực hiện các bước lặp lại, tách các hàm điều phối tái sử dụng:

```python
@dataclass
class PreparedTurn:
    session_id: str
    last_message: str
    chat_history_str: str
    domain: str
    queries: list[str]
    query_vector: Optional[list[float]] = None
    cached_response: Optional[dict[str, Any]] = None

async def prepare_turn_context(request: ChatRequest) -> PreparedTurn:
    """Xử lý toàn bộ logic chuẩn bị lịch sử, rewriting và kiểm tra cache."""
    ...

async def retrieve_turn_context(
    pipeline: RAGPipeline,
    last_message: str,
    domain: str,
    queries: list[str],
    category: Optional[str] = None,
) -> tuple[list[Document], str, list[dict[str, Any]]]:
    """Thực hiện aretrieve và format_for_frontend có quản lý token budget."""
    ...

async def finalize_turn(
    request: ChatRequest,
    session_id: str,
    user_content: str,
    generated_text: str,
    frontend_context: list[dict[str, Any]],
    query_vector: Optional[list[float]],
    domain: str,
    retrieved_docs: list[Document],
) -> tuple[str, list[dict[str, Any]]]:
    """Xác thực trích dẫn, cập nhật cache, lưu trữ Postgres và trigger summary."""
    ...
```

**Lợi ích:**
- `chat_endpoint` chỉ còn ~35 dòng: gọi `prepare_turn_context` -> nếu có cache return ngay -> nếu không gọi `retrieve_turn_context` -> gọi LLM `ainvoke` -> gọi `finalize_turn` -> return JSON.
- `chat_stream_endpoint` chỉ còn ~60 dòng: gọi `prepare_turn_context` -> nếu cache thì phát tokens -> nếu không gọi `retrieve_turn_context` -> stream qua SSE -> gọi `finalize_turn` -> emit done.

### 3. Tối ưu hóa Thuật toán Vector Thưa (`sparse_vector.py`)
- **Hiện tại:**
  ```python
  indices = []
  values = []
  for token, count in tf_counts.items():
      index = self._hash_token(token)
      if index in indices:          # Quét mảng tuyến tính O(N)
          idx_pos = indices.index(index)
          values[idx_pos] += float(count)
      else:
          indices.append(index)
          values.append(float(count))
  ```
- **Tối ưu:**
  ```python
  sparse_map: dict[int, float] = {}
  for token, count in tf_counts.items():
      index = self._hash_token(token)
      sparse_map[index] = sparse_map.get(index, 0.0) + float(count)
  return {
      "indices": list(sparse_map.keys()),
      "values": list(sparse_map.values()),
  }
  ```
- **Kết quả:** Xử lý collision tức thì trong $O(1)$ thay vì $O(N^2)$.

### 4. Loại bỏ Dynamic Reflection trong `pipeline.py`
- Thay vì gọi `inspect.signature(...)` trên mỗi request trong các hàm `retrieve` và `aretrieve`, `RAGPipeline` kiểm tra cờ tham số `_searcher_supports_api_key` và `_reranker_supports_api_key` một lần duy nhất trong `__init__`.

### 5. Hiện đại hóa FastAPI Lifespan trong `backend/app/main.py`
- Thay thế decorator cũ `@application.on_event("startup")` bằng:
  ```python
  from contextlib import asynccontextmanager

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Startup logic
      app.state.local_models_ready = not LOCAL_MODELS_PRELOAD_ENABLED
      app.state.local_models_error = None
      app.state.runtime_config_error = None
      if CHAT_STORAGE_MODE == "postgres":
          logger.warning(...)
      await asyncio.to_thread(load_knowledge_base)
      asyncio.create_task(asyncio.to_thread(_initialize_runtime_components_sync))
      logger.info("Document metadata loaded; remaining initialization scheduled in background")
      yield
      # Shutdown logic (nếu cần cleanup resources)
  ```
- Khởi tạo app bằng `FastAPI(..., lifespan=lifespan)`.

---

## Verification & Testing Strategy
1. **Toàn bộ Unit & Integration tests:**
   - Chạy `PYTHONPATH=. .venv/bin/pytest tests/` để đảm bảo 124 tests đều pass 100%.
2. **Kiểm thử thực tế cả 2 luồng:**
   - Test `POST /chat` (non-streaming): xác nhận cache hit/miss, kết quả trả về đúng chuẩn JSON.
   - Test `POST /chat/stream` (SSE streaming): xác nhận token chảy mượt mà, event `done` và `context` phát đúng trình tự.
   - Test `DELETE /chat/session/{id}`: xác nhận xóa session thành công.
3. **Kiểm tra Log & Cảnh báo:**
   - Xác nhận log khởi động server không còn bất kỳ dòng `DeprecationWarning: on_event is deprecated`.
