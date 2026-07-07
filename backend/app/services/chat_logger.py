import os
import json
import uuid
from datetime import datetime
from threading import Lock
from pathlib import Path

from app.config import JSON_DATA_PATH
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.services.chat_logger")

DATA_DIR = os.path.dirname(JSON_DATA_PATH)
CHAT_LOGS_FILE = os.path.join(DATA_DIR, "chat_logs.json")
_lock = Lock()

def _ensure_log_file():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(CHAT_LOGS_FILE):
        with open(CHAT_LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

def log_interaction(session_id: str, user_message: str, ai_response: str):
    """Lưu trữ một lượt chat vào file JSON."""
    _ensure_log_file()
    
    entry = {
        "id": str(uuid.uuid4()),
        "session_id": session_id or "unknown",
        "user_message": user_message,
        "ai_response": ai_response,
        "timestamp": datetime.now().isoformat(),
    }
    
    try:
        with _lock:
            with open(CHAT_LOGS_FILE, "r", encoding="utf-8") as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
            
            logs.append(entry)
            
            with open(CHAT_LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
    except Exception as e:
        logger.error(f"Failed to log chat interaction: {e}")

def get_chat_logs():
    """Lấy toàn bộ lịch sử chat."""
    _ensure_log_file()
    try:
        with _lock:
            with open(CHAT_LOGS_FILE, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
    except Exception as e:
        logger.error(f"Failed to read chat logs: {e}")
        return []
