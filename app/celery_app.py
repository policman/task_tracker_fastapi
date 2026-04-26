from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "production_tasks",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    include=["app.tasks.production_tasks"]
)