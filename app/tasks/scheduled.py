import asyncio

from app.celery_app import celery_app
from app.core.cache import RedisService
from app.core.config import settings
from app.core.database import DatabaseHelper
from app.domain.services.batch_service import BatchService
from app.domain.services.webhook_service import WebhookService
from app.storage.minio_service import storage_service
from app.tasks.webhooks import send_webhook_delivery


@celery_app.task
def auto_close_expired_batches():
    async def _logic():
        local_db = DatabaseHelper(database_url=settings.database_url, echo=False)
        try:
            async with local_db.session_factory() as session:
                batch_service = BatchService(session)
                closed_count = await batch_service.auto_close_expired_batches()
                return {"success": True, "closed_count": closed_count}
        finally:
            await local_db.dispose()

    return asyncio.run(_logic())


@celery_app.task
def cleanup_old_files():
    deleted_reports = storage_service.cleanup_old_files(
        bucket=settings.minio.bucket_reports, days_old=30
    )
    deleted_exports = storage_service.cleanup_old_files(
        bucket=settings.minio.bucket_exports, days_old=30
    )

    return {
        "success": True,
        "deleted_reports": deleted_reports,
        "deleted_exports": deleted_exports,
        "total_deleted": deleted_reports + deleted_exports,
    }


@celery_app.task
def update_cached_statistics():
    async def _logic():
        local_db = DatabaseHelper(database_url=settings.database_url, echo=False)
        redis = RedisService()
        try:
            async with local_db.session_factory() as session:
                service = BatchService(session)
                stats_data = await service.get_dashboard_statistics()

                await redis.set_cache("dashboard_stats", stats_data, 300)

                return {"success": True, "stats": stats_data}
        finally:
            await local_db.dispose()
            await redis.close()

    return asyncio.run(_logic())


@celery_app.task
def retry_failed_webhooks():
    async def _logic():
        local_db = DatabaseHelper(database_url=settings.database_url, echo=False)
        try:
            async with local_db.session_factory() as session:
                webhook_service = WebhookService(session)
                deliveries_list = await webhook_service.get_deliveries_for_retry()

                for delivery in deliveries_list:
                    send_webhook_delivery.delay(delivery.id)

                return {"enqueued_retries": len(deliveries_list)}
        finally:
            await local_db.dispose()

    return asyncio.run(_logic())
