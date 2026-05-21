from celery import Celery
from app.core.config import settings
from celery.schedules import crontab

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
    include=[
        "app.tasks.aggregation",
        "app.tasks.reports",
        "app.tasks.imports",
        "app.tasks.exports",
    ]
)

# celery_app.conf.beat_schedule = {
#     "close-expired-batches-every-night": {
#         "task": "auto_close_expired_batches", # Имя таски из production_tasks
#         "schedule": crontab(hour=0, minute=0), # Запускать в 00:00 каждый день
#     },
# }