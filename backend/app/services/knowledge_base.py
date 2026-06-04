"""
Knowledge Base — Quản lý dữ liệu pháp luật trong RAM.
Tách riêng từ vectorstore.py để các module khác có thể truy cập
mà không phụ thuộc vào vector store.
"""
import os
import json
import glob
from typing import Dict, Any, List, Optional

from app.config import JSON_DATA_PATH
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.knowledge_base")

# --- DỮ LIỆU TOÀN CỤC ---
KNOWLEDGE_BASE: Dict[str, Any] = {}
LAW_METADATA: Dict[str, Any] = {}


def determine_category(law_name: str) -> str:
    """Phân loại văn bản pháp luật dựa trên tên gọi để dễ dàng lọc (filter) sau này."""
    name_lower = law_name.lower()

    # Gom nhóm các từ khóa liên quan để code gọn hơn
    if any(kw in name_lower for kw in ["kinh doanh", "doanh nghiệp", "thương mại"]):
        return "Kinh doanh"
    if "đất đai" in name_lower:
        return "Đất đai"
    if "môi trường" in name_lower:
        return "Bảo vệ môi trường"
    if "tố tụng" in name_lower:
        return "Tố tụng dân sự"
    if "nhà ở" in name_lower:
        return "Nhà ở"

    return "Khác"


def load_knowledge_base() -> None:
    """Nạp toàn bộ dữ liệu JSON vào RAM để Chatbot truy xuất siêu tốc."""
    global KNOWLEDGE_BASE, LAW_METADATA
    json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))

    logger.info("Đang nạp %d file JSON vào bộ nhớ...", len(json_files))

    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            law_info = data.get("law_info", {})
            clauses = data.get("clauses", [])

            law_id = law_info.get("law_id")
            law_name = law_info.get("law_name", "")

            # Lưu trữ thông tin chung của văn bản luật
            LAW_METADATA[law_id] = {
                "law_name": law_name,
                "summary": law_info.get("executive_summary", ""),
                "category": determine_category(law_name)
            }

            # Lưu trữ chi tiết từng điều khoản
            for clause in clauses:
                KNOWLEDGE_BASE[clause["id"]] = {
                    "law_id": law_id,
                    "position": clause.get("position", {}),
                    "content": clause.get("content", ""),
                    "cross_references": clause.get("cross_references", [])
                }

    logger.info(
        "Nạp dữ liệu vào RAM hoàn tất! (%d điều khoản, %d văn bản)",
        len(KNOWLEDGE_BASE), len(LAW_METADATA)
    )


def get_clause(clause_id: str) -> Optional[Dict[str, Any]]:
    """Truy xuất một điều khoản theo ID."""
    return KNOWLEDGE_BASE.get(clause_id)


def get_law_metadata(law_id: str) -> Optional[Dict[str, Any]]:
    """Truy xuất metadata của một văn bản luật."""
    return LAW_METADATA.get(law_id)


def resolve_reference_data(target_id: str) -> List[Dict[str, Any]]:
    """Tìm chính xác Khoản hoặc gom tất cả các Khoản của một Điều."""
    if target_id in KNOWLEDGE_BASE:
        return [KNOWLEDGE_BASE[target_id]]

    results = []
    search_prefix = f"{target_id}_"
    for k, v in KNOWLEDGE_BASE.items():
        if k.startswith(search_prefix):
            results.append(v)
    return results
