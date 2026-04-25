import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from core.config import settings
from api.v1.routers import product, batches, files
from app.storage.minio_service import storage_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("- Запуск сервера. Инициализация хранилища...")
    try:
        storage_service.init_buckets()
    except Exception as e:
        print(f"х Ошибка подключения к MinIO: {e}")

    yield
    print("- Остановка сервера")
app = FastAPI(
    title="Production Control API",
    description="API для системы управления производством (Завод)",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(batches.router, prefix="/api/v1")
app.include_router(product.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True
    )