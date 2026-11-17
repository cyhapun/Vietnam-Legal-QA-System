"""
Quản lý cấu hình tập trung cho backend.
Tất cả đường dẫn, hằng số, và biến môi trường được khai báo tại đây.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# --- NẠP BIẾN MÔI TRƯỜNG ---
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_env_path = _backend_dir.parent / ".env"

if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

# --- ĐƯỜNG DẪN DỮ LIỆU ---
JSON_DATA_PATH = str(_backend_dir / "data" / "processed")
FAISS_INDEX_PATH = str(_backend_dir / "vietlaw_faiss_index")
TRACKING_FILE = str(_backend_dir / "embedded_files.json")

# --- API KEYS ---
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

# Runtime profile
_runtime_profile_env = os.getenv("RUNTIME_PROFILE", "").strip().lower()
RUNTIME_PROFILE = _runtime_profile_env or (
    "serverless" if os.getenv("VERCEL") or os.getenv("VERCEL_ENV") else "local"
)
SUPPORTED_RUNTIME_PROFILES = frozenset({"local", "serverless"})

# Chat storage mode
CHAT_STORAGE_MODE = os.getenv("CHAT_STORAGE_MODE", "postgres").strip().lower()
FRONTEND_CHAT_STORAGE_MODE = os.getenv("NEXT_PUBLIC_CHAT_STORAGE_MODE", "").strip().lower()
SUPPORTED_CHAT_STORAGE_MODES = frozenset({"postgres", "browser"})

# --- STORAGE BACKEND ---
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "qdrant_postgres").strip().lower()
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:15432/vietlaw")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "vietlaw_clauses")
DISABLE_AUTO_INGEST = os.getenv("DISABLE_AUTO_INGEST", "true").strip().lower() == "true"
ENABLE_FAISS_FALLBACK = False
PIPELINE_TIMING_ENABLED = os.getenv("PIPELINE_TIMING_ENABLED", "false").strip().lower() == "true"

# --- THÔNG SỐ EMBEDDING ---
DEFAULT_LOCAL_EMBEDDING_MODEL = "../models/embedding/vietlaw-bge-m3-finetuned/best"
DEFAULT_LOCAL_RERANKER_MODEL = "../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected"
DEFAULT_REMOTE_EMBEDDING_MODEL = "BAAI/bge-m3"

_default_embedding_mode = "api" if RUNTIME_PROFILE == "serverless" else "local"
HUGGINGFACE_EMBEDDING_MODE = os.getenv(
    "HUGGINGFACE_EMBEDDING_MODE",
    _default_embedding_mode,
).strip().lower()
_default_embedding_model = (
    DEFAULT_REMOTE_EMBEDDING_MODEL
    if HUGGINGFACE_EMBEDDING_MODE == "api"
    else DEFAULT_LOCAL_EMBEDDING_MODEL
)
EMBEDDING_MODEL = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", _default_embedding_model)
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").strip().lower()
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu").strip()
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
EMBEDDING_NORMALIZE = True
LOCAL_MODELS_OFFLINE = True
_local_preload_requested = os.getenv("LOCAL_MODELS_PRELOAD_ENABLED", "true").strip().lower() == "true"
_local_warmup_requested = os.getenv("LOCAL_MODELS_WARMUP_ENABLED", "true").strip().lower() == "true"
LOCAL_MODELS_PRELOAD_ENABLED = _local_preload_requested and RUNTIME_PROFILE == "local"
LOCAL_MODELS_WARMUP_ENABLED = _local_warmup_requested and RUNTIME_PROFILE == "local"
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_MAX_RETRIES = 3
EMBEDDING_SLEEP_BETWEEN_BATCHES = 5.0
EMBEDDING_RETRY_BASE_WAIT = 15.0

# Ollama defaults (tương thích backward nếu có import cũ)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = "bge-m3"
OLLAMA_EMBEDDING_TIMEOUT = 300.0

# --- THÔNG SỐ RETRIEVAL ---
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "5"))
RETRIEVER_CANDIDATE_K = int(os.getenv("RETRIEVER_CANDIDATE_K", "20"))
RETRIEVER_FETCH_K = 20
RETRIEVER_LAMBDA_MULT = 0.8
CONTEXT_TOKEN_BUDGET = int(os.getenv("CONTEXT_TOKEN_BUDGET", "6000"))
MAX_CITATIONS = int(os.getenv("MAX_CITATIONS", "5"))
HISTORY_MESSAGES = int(os.getenv("HISTORY_MESSAGES", "4"))
MAX_SUBQUERIES = int(os.getenv("MAX_SUBQUERIES", "3"))

# --- THÔNG SỐ LLM (GOOGLE AI STUDIO) ---
GOOGLE_API_KEYS = os.getenv("GOOGLE_API_KEYS", "") or os.getenv("GOOGLE_API_KEY", "")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.1-flash-lite").strip()
GOOGLE_FALLBACK_MODELS = os.getenv("GOOGLE_FALLBACK_MODELS", "gemini-2.5-flash-lite,gemini-2.5-flash").strip()
GOOGLE_FALLBACK_MODEL = GOOGLE_MODEL  # Backward compatibility
ENABLE_GOOGLE_FALLBACK = True  # Backward compatibility
LLM_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "1500"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_REPETITION_PENALTY = 1.0
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))
GOOGLE_OPENAI_BASE_URL = os.getenv(
    "GOOGLE_OPENAI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
).strip()

# --- CORS ---
CORS_ORIGINS = ["*"]

# --- PIPELINE CONFIG ---
PIPELINE_CONFIG = {
    "chunking": "clause",
    "search": os.getenv("PIPELINE_SEARCH", "hybrid").strip().lower(),
    "reranking": os.getenv(
        "PIPELINE_RERANKING",
        "embedding_similarity" if RUNTIME_PROFILE == "serverless" else "cross_encoder",
    ).strip().lower(),
    "context_builder": "nested",
    "hybrid_vector_weight": 0.5,
    "hybrid_bm25_weight": 0.5,
    "reranker_model": os.getenv("RERANKER_MODEL", DEFAULT_LOCAL_RERANKER_MODEL),
    "reranker_max_candidates": 10,
    "reranker_device": "cpu",
    "reranker_batch_size": 8,
    "reranker_max_length": 512,
    "reranker_fail_open": False,
    "rewriter": os.getenv("PIPELINE_REWRITER", "llm").strip().lower(),
}

# --- SEMANTIC CACHE ---
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true").strip().lower() == "true"
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))
SEMANTIC_CACHE_COLLECTION = os.getenv("SEMANTIC_CACHE_COLLECTION", "semantic_cache")

# --- INFERENCE STRATEGY (Remote-only via Google AI Studio) ---
INFERENCE_STRATEGY = "remote_first"


def validate_runtime_configuration() -> None:
    """Validate profile/provider combinations without loading model weights."""
    if CHAT_STORAGE_MODE not in SUPPORTED_CHAT_STORAGE_MODES:
        raise ValueError(
            f"CHAT_STORAGE_MODE must be one of {sorted(SUPPORTED_CHAT_STORAGE_MODES)}; "
            f"got {CHAT_STORAGE_MODE!r}."
        )
    if FRONTEND_CHAT_STORAGE_MODE and FRONTEND_CHAT_STORAGE_MODE not in SUPPORTED_CHAT_STORAGE_MODES:
        raise ValueError(
            "NEXT_PUBLIC_CHAT_STORAGE_MODE must be one of "
            f"{sorted(SUPPORTED_CHAT_STORAGE_MODES)}; got {FRONTEND_CHAT_STORAGE_MODE!r}."
        )
    if FRONTEND_CHAT_STORAGE_MODE and FRONTEND_CHAT_STORAGE_MODE != CHAT_STORAGE_MODE:
        raise ValueError(
            "CHAT_STORAGE_MODE and NEXT_PUBLIC_CHAT_STORAGE_MODE must match."
        )
    if RUNTIME_PROFILE not in SUPPORTED_RUNTIME_PROFILES:
        raise ValueError(
            f"RUNTIME_PROFILE must be one of {sorted(SUPPORTED_RUNTIME_PROFILES)}; "
            f"got {RUNTIME_PROFILE!r}."
        )
    if HUGGINGFACE_EMBEDDING_MODE not in {"api", "local"}:
        raise ValueError("HUGGINGFACE_EMBEDDING_MODE must be either 'api' or 'local'.")
    if RUNTIME_PROFILE == "serverless" and HUGGINGFACE_EMBEDDING_MODE != "api":
        raise ValueError("RUNTIME_PROFILE=serverless requires HUGGINGFACE_EMBEDDING_MODE=api.")
    if RUNTIME_PROFILE == "local" and HUGGINGFACE_EMBEDDING_MODE != "local":
        raise ValueError("RUNTIME_PROFILE=local requires HUGGINGFACE_EMBEDDING_MODE=local.")
    if RUNTIME_PROFILE == "local" and (
        not Path(EMBEDDING_MODEL).is_absolute()
        and not EMBEDDING_MODEL.startswith((".", "~"))
    ):
        raise ValueError(
            "Local embedding mode requires HUGGINGFACE_EMBEDDING_MODEL to be a filesystem path."
        )
    if RUNTIME_PROFILE == "serverless" and (
        Path(EMBEDDING_MODEL).is_absolute()
        or EMBEDDING_MODEL.startswith((".", "~"))
    ):
        raise ValueError(
            "Serverless embedding mode requires HUGGINGFACE_EMBEDDING_MODEL to be a Hub model id."
        )
    if RUNTIME_PROFILE == "local" and PIPELINE_CONFIG["reranking"] in {
        "embedding_similarity",
        "remote_embedding_similarity",
    }:
        raise ValueError(
            "Local runtime must use cross_encoder or none for reranking."
        )


def runtime_profile_summary() -> dict:
    """Return safe profile diagnostics for readiness and startup logs."""
    return {
        "profile": RUNTIME_PROFILE,
        "chatStorageMode": CHAT_STORAGE_MODE,
        "frontendChatStorageMode": FRONTEND_CHAT_STORAGE_MODE or None,
        "embeddingMode": HUGGINGFACE_EMBEDDING_MODE,
        "embeddingModel": EMBEDDING_MODEL,
        "reranking": PIPELINE_CONFIG["reranking"],
        "localModelsPreload": LOCAL_MODELS_PRELOAD_ENABLED,
    }


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
