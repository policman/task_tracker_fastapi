from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.exception_handlers import app_exception_handler, global_exception_handler
from app.api.v1.routers import analytics, batches, products, tasks, webhooks
from app.core.config import settings
from app.core.exceptions import BaseAppException
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

app.add_exception_handler(BaseAppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(batches.router)
app.include_router(products.router)
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(webhooks.router)

if __name__ == "__main__":
    uvicorn.run(
        app="app.main:app", host=settings.run.host, port=settings.run.port, reload=True
    )
