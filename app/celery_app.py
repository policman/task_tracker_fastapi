from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "production_tasks",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=[
        "app.tasks.aggregation",
        "app.tasks.reports",
        "app.tasks.imports",
        "app.tasks.exports",
        "app.tasks.scheduled",
        "app.tasks.webhooks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "auto-close-expired-batches": {
        "task": "app.tasks.scheduled.auto_close_expired_batches",
        # "schedule": crontab(hour=1, minute=0),
        "schedule": crontab(hour=0, minute=1),
    },
    "cleanup-old-files": {
        "task": "app.tasks.scheduled.cleanup_old_files",
        # "schedule": crontab(hour=2, minute=0),
        "schedule": crontab(hour=0, minute=1),
    },
    "update-statistics": {
        "task": "app.tasks.scheduled.update_cached_statistics",
        # "schedule": crontab(minute="*/5"),
        "schedule": crontab(minute="*/1"),
    },
    "retry-failed-webhooks": {
        "task": "app.tasks.scheduled.retry_failed_webhooks",
        # "schedule": crontab(minute="*/15"),
        "schedule": crontab(minute="*/1"),
    },
}
