from fastapi import APIRouter
from app.services.storage import get_all_chat_messages

router = APIRouter()

@router.get("/analytics/logs")
async def get_logs(page: int = 1, limit: int = 50):
    """Lấy lịch sử chat có phân trang."""
    logs = get_all_chat_messages()
    # Sort by timestamp descending
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    start = (page - 1) * limit
    end = start + limit
    
    return {
        "total": len(logs),
        "page": page,
        "limit": limit,
        "data": logs[start:end]
    }

@router.get("/analytics/stats")
async def get_stats():
    """Lấy thống kê cơ bản."""
    logs = get_all_chat_messages()
    
    # Simple stats: total chats, and breakdown by date
    stats_by_date = {}
    for log in logs:
        # e.g., '2026-07-07T08:17:48.123' -> '2026-07-07'
        date = log.get("timestamp", "").split("T")[0] if log.get("timestamp") else "unknown"
        stats_by_date[date] = stats_by_date.get(date, 0) + 1
        
    return {
        "total_interactions": len(logs),
        "by_date": stats_by_date
    }
