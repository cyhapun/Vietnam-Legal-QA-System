"""
Điểm vào chính của backend — FastAPI Application Factory.
File này chỉ chịu trách nhiệm:
  1. Tạo FastAPI app
  2. Đăng ký middleware
  3. Đăng ký routers
  4. Khởi tạo RAG Pipeline khi startup
"""
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.api.chat import router as chat_router
from app.services.pipeline import init_pipeline
from app.services.storage import initialize_storage
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.main")


def create_app() -> FastAPI:
    """Application factory — tạo và cấu hình FastAPI app."""
    application = FastAPI(title="VietLaw RAG Backend")

    # --- CORS Middleware ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Đăng ký Routers ---
    application.include_router(chat_router)

    async def _initialize_runtime_components() -> None:
        logger.info("Khởi tạo storage layer...")
        try:
            initialize_storage()
        except Exception as e:
            logger.warning("Không thể khởi tạo storage layer DB-backed: %s", str(e))

        logger.info("Khởi tạo RAG Pipeline...")
        try:
            init_pipeline()
            logger.info("RAG Pipeline đã sẵn sàng!")
        except Exception as e:
            logger.error("Lỗi khởi tạo RAG Pipeline: %s", str(e))
            logger.warning("Backend sẽ tiếp tục chạy ở chế độ degraded; API có thể dùng fallback retrieval.")

    # --- Startup Event ---
    @application.on_event("startup")
    async def startup_event():
        """Schedule initialization as non-blocking background task, don't wait for it."""
        # Schedule background task but don't await - server binds to port immediately
        asyncio.create_task(_initialize_runtime_components())
        logger.info("Initialization scheduled as background task, server ready to receive requests")

    return application


# Tạo app instance
app = create_app()

# --- KHỞI CHẠY SERVER ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
