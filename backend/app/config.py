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
FAISS_INDEX_PATH = str(_backend_dir / "vietlaw_faiss_index")
JSON_DATA_PATH = str(_backend_dir / "data" / "processed")
TRACKING_FILE = str(_backend_dir / "embedded_files.json")

# --- API KEYS ---
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# --- THÔNG SỐ EMBEDDING ---
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_MAX_RETRIES = 3
EMBEDDING_SLEEP_BETWEEN_BATCHES = 5  # seconds
EMBEDDING_RETRY_BASE_WAIT = 15  # seconds

# --- THÔNG SỐ RETRIEVAL ---
RETRIEVER_K = 6
RETRIEVER_FETCH_K = 20
RETRIEVER_LAMBDA_MULT = 0.8

# --- THÔNG SỐ LLM ---
LLM_MAX_NEW_TOKENS = 1500
LLM_TEMPERATURE = 0.1
LLM_REPETITION_PENALTY = 1.1
LLM_TIMEOUT = 300

# --- CORS ---
CORS_ORIGINS = ["*"]
