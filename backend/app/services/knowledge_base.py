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

ALL_LAWS_CATEGORY = "all"
CIVIL_FAMILY_PERSONAL_CATEGORY = "civil-family-personal"
LAND_PROPERTY_ENVIRONMENT_CATEGORY = "land-property-environment"
TRAFFIC_ORDER_SANCTIONS_CATEGORY = "traffic-order-sanctions"

_LEGACY_CATEGORY_ALIASES = {
    "Chung": ALL_LAWS_CATEGORY,
    "Kinh doanh": LAND_PROPERTY_ENVIRONMENT_CATEGORY,
    "Đất đai": LAND_PROPERTY_ENVIRONMENT_CATEGORY,
    "Bảo vệ môi trường": LAND_PROPERTY_ENVIRONMENT_CATEGORY,
    "Tố tụng dân sự": CIVIL_FAMILY_PERSONAL_CATEGORY,
    "Nhà ở": LAND_PROPERTY_ENVIRONMENT_CATEGORY,
}


def determine_category(law_name: str) -> str:
    """Phân loại văn bản vào một trong ba nhóm pháp luật của giao diện."""
    name_lower = law_name.lower()

    if any(
        keyword in name_lower
        for keyword in [
            "dân sự",
            "hôn nhân",
            "gia đình",
            "hộ tịch",
            "nhân thân",
        ]
    ):
        return CIVIL_FAMILY_PERSONAL_CATEGORY

    if any(
        keyword in name_lower
        for keyword in [
            "đất đai",
            "bất động sản",
            "nhà ở",
            "xây dựng",
            "môi trường",
            "tài nguyên",
        ]
    ):
        return LAND_PROPERTY_ENVIRONMENT_CATEGORY

    if any(
        keyword in name_lower
        for keyword in [
            "giao thông",
            "đường bộ",
            "đường sắt",
            "hàng hải",
            "hàng không",
            "trật tự",
            "vi phạm hành chính",
            "xử phạt",
        ]
    ):
        return TRAFFIC_ORDER_SANCTIONS_CATEGORY

    # Luật chưa thuộc ba nhóm vẫn có thể được tìm qua "Tất cả các luật".
    return ALL_LAWS_CATEGORY


def normalize_category(category: Optional[str]) -> str:
    """Chuẩn hóa category mới và các giá trị cũ còn được client gửi lên."""
    if not category:
        return ALL_LAWS_CATEGORY
    return _LEGACY_CATEGORY_ALIASES.get(category, category)


def document_matches_category(
    metadata: Dict[str, Any],
    category: Optional[str],
) -> bool:
    """Kiểm tra document theo law_id, tương thích cả FAISS index cũ."""
    normalized_category = normalize_category(category)
    if normalized_category == ALL_LAWS_CATEGORY:
        return True

    law_id = metadata.get("law_id")
    law_metadata = LAW_METADATA.get(law_id, {})
    document_category = law_metadata.get("category")

    if not document_category:
        document_category = normalize_category(metadata.get("category"))

    return document_category == normalized_category


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
