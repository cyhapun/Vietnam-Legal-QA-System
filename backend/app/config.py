"""
Quản lý cấu hình tập trung cho backend.
Tất cả đường dẫn, hằng số, và biến môi trường được khai báo tại đây.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# --- NẠP BIẾN MÔI TRƯỜNG ---
# Tìm file .env ở thư mục root project (2 cấp trên app/)
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_env_path = _backend_dir.parent / ".env"

if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

# --- ĐƯỜNG DẪN DỮ LIỆU ---
# Sử dụng đường dẫn tuyệt đối tính từ thư mục backend/
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").strip().lower()
_embedding_artifact_suffix = (
    "" if EMBEDDING_PROVIDER == "huggingface" else f"_{EMBEDDING_PROVIDER}"
)

FAISS_INDEX_PATH = os.getenv(
    "FAISS_INDEX_PATH",
    str(_backend_dir / f"vietlaw_faiss_index{_embedding_artifact_suffix}"),
)
JSON_DATA_PATH = str(_backend_dir / "data" / "processed")
TRACKING_FILE = os.getenv(
    "EMBEDDED_FILES_PATH",
    str(_backend_dir / f"embedded_files{_embedding_artifact_suffix}.json"),
)

# --- API KEYS ---
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# --- STORAGE BACKEND ---
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "faiss").strip().lower()
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/vietlaw")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "vietlaw_clauses")
DISABLE_AUTO_INGEST = os.getenv("DISABLE_AUTO_INGEST", "false").strip().lower() == "true"

# --- THÔNG SỐ EMBEDDING ---
EMBEDDING_MODEL = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "BAAI/bge-m3")
# Hỗ trợ "api" hoặc "local"
HUGGINGFACE_EMBEDDING_MODE = os.getenv("HUGGINGFACE_EMBEDDING_MODE", "local").strip().lower()
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu").strip()
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
EMBEDDING_NORMALIZE = os.getenv("EMBEDDING_NORMALIZE", "true").strip().lower() == "true"
LOCAL_MODELS_OFFLINE = os.getenv("LOCAL_MODELS_OFFLINE", "true").strip().lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
OLLAMA_EMBEDDING_TIMEOUT = float(os.getenv("OLLAMA_EMBEDDING_TIMEOUT", "300"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
EMBEDDING_SLEEP_BETWEEN_BATCHES = float(os.getenv(
    "EMBEDDING_SLEEP_BETWEEN_BATCHES",
    "0" if EMBEDDING_PROVIDER == "ollama" else "5",
))
EMBEDDING_RETRY_BASE_WAIT = float(os.getenv(
    "EMBEDDING_RETRY_BASE_WAIT",
    "2" if EMBEDDING_PROVIDER == "ollama" else "15",
))

# --- THÔNG SỐ RETRIEVAL ---
RETRIEVER_K = 20
RETRIEVER_CANDIDATE_K = int(os.getenv("RETRIEVER_CANDIDATE_K", "60"))
RETRIEVER_FETCH_K = 20
RETRIEVER_LAMBDA_MULT = 0.8

# --- THÔNG SỐ LLM ---
LLM_MAX_NEW_TOKENS = 1500
LLM_TEMPERATURE = 0.1
LLM_REPETITION_PENALTY = 1.0
LLM_TIMEOUT = 300
ENABLE_GOOGLE_FALLBACK = os.getenv("ENABLE_GOOGLE_FALLBACK", "false").strip().lower() == "true"
GOOGLE_FALLBACK_MODEL = os.getenv("GOOGLE_FALLBACK_MODEL", "gemini-3.1-flash-lite").strip()
GOOGLE_OPENAI_BASE_URL = os.getenv(
    "GOOGLE_OPENAI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
).strip()

# --- CORS ---
CORS_ORIGINS = ["*"]

# ---------------------------------------------------------------------------
# PIPELINE CONFIG — Thay đổi ở đây để chạy ablation study
# ---------------------------------------------------------------------------
# Mỗi key chọn strategy tương ứng. Xem danh sách strategy ở từng module.
#
# Ví dụ ablation experiments:
#   Baseline:  search="faiss",  reranking="none"
#   +Reranker: search="faiss",  reranking="cross_encoder"
#   Hybrid:    search="hybrid", reranking="none"
#   Full:      search="hybrid", reranking="cross_encoder"
# ---------------------------------------------------------------------------
PIPELINE_CONFIG = {
    # Chunking: "clause" (mỗi khoản = 1 chunk)
    "chunking": os.getenv("PIPELINE_CHUNKING", "clause"),

    # Search: "faiss" | "bm25" | "hybrid"
    "search": os.getenv("PIPELINE_SEARCH", "faiss"),

    # Reranking: "none" | "cross_encoder"
    "reranking": os.getenv("PIPELINE_RERANKING", "none"),

    # Context builder: "nested"
    "context_builder": os.getenv("PIPELINE_CONTEXT_BUILDER", "nested"),

    # --- Hybrid search weights (chỉ dùng khi search="hybrid") ---
    "hybrid_vector_weight": float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.5")),
    "hybrid_bm25_weight": float(os.getenv("HYBRID_BM25_WEIGHT", "0.5")),

    # --- Reranker model (chỉ dùng khi reranking="cross_encoder") ---
    "reranker_model": os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
    "reranker_max_candidates": int(os.getenv("RERANKER_MAX_CANDIDATES", "20")),
    "reranker_device": os.getenv("RERANKER_DEVICE", "cpu").strip(),
    "reranker_batch_size": int(os.getenv("RERANKER_BATCH_SIZE", "8")),
    "reranker_max_length": int(os.getenv("RERANKER_MAX_LENGTH", "512")),
    "reranker_fail_open": os.getenv("RERANKER_FAIL_OPEN", "false").strip().lower() == "true",

    # --- Query Rewriter ---
    "rewriter": os.getenv("PIPELINE_REWRITER", "none"),
    "rewriter_model_provider": os.getenv("REWRITER_MODEL_PROVIDER", "ollama"),
    "rewriter_model_name": os.getenv("REWRITER_MODEL_NAME", "qwen2.5:1.5b"),
}

# --- SEMANTIC CACHE ---
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true").strip().lower() == "true"
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))
SEMANTIC_CACHE_COLLECTION = os.getenv("SEMANTIC_CACHE_COLLECTION", "semantic_cache")

# --- FALLBACK STRATEGY ---
INFERENCE_STRATEGY = os.getenv("INFERENCE_STRATEGY", "remote_first").strip().lower()


def _validate_positive_int(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0; got {value}.")


def _validate_non_empty(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty.")


_validate_positive_int("EMBEDDING_BATCH_SIZE", EMBEDDING_BATCH_SIZE)
_validate_positive_int("EMBEDDING_DIMENSION", EMBEDDING_DIMENSION)
_validate_positive_int("RERANKER_BATCH_SIZE", PIPELINE_CONFIG["reranker_batch_size"])
_validate_positive_int("RERANKER_MAX_LENGTH", PIPELINE_CONFIG["reranker_max_length"])
_validate_non_empty("QDRANT_COLLECTION", QDRANT_COLLECTION)
_validate_non_empty("SEMANTIC_CACHE_COLLECTION", SEMANTIC_CACHE_COLLECTION)
