from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.v1.routers import analytics, batches, products, tasks, webhooks
from app.core.config import settings
from scripts.minio_init import init_buckets


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Init Minio")
    try:
        init_buckets()
    except Exception as e:
        print(f"Minio connection error: {e}")

    yield


app = FastAPI(title="Production Control API", version="1.0.0", lifespan=lifespan)

app.include_router(batches.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(app="main:app", host=settings.run.host, port=settings.run.port, reload=True)
