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

# --- THÔNG SỐ EMBEDDING ---
EMBEDDING_MODEL = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "BAAI/bge-m3")
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
RETRIEVER_K = 6
RETRIEVER_CANDIDATE_K = int(os.getenv("RETRIEVER_CANDIDATE_K", "30"))
RETRIEVER_FETCH_K = 20
RETRIEVER_LAMBDA_MULT = 0.8

# --- THÔNG SỐ LLM ---
LLM_MAX_NEW_TOKENS = 1500
LLM_TEMPERATURE = 0.1
LLM_REPETITION_PENALTY = 1.1
LLM_TIMEOUT = 300

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
}
