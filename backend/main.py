"""
Backward-compatible entry point.
Chạy: python main.py  HOẶC  uvicorn app.main:app --reload
File này tồn tại để giữ khả năng chạy bằng `python main.py` như cũ.
Logic thực tế nằm trong package app/
"""
import uvicorn
from app.main import app  # noqa: F401 - import để uvicorn tìm được

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)