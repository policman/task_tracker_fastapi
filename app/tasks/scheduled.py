import asyncio

from app.celery_app import celery_app
from app.core.cache import RedisService
from app.core.config import settings
from app.core.database import db_helper
from app.data.repositories.batch_repository import BatchRepository
from app.data.repositories.webhook_repository import WebhookRepository
from app.storage.minio_service import storage_service
from app.tasks.webhooks import send_webhook_delivery


@celery_app.task
def auto_close_expired_batches():
    async def _logic():
        try:
            async with db_helper.session_factory() as session:
                batch_repo = BatchRepository(session)
                closed_count = await batch_repo.auto_close_expired_batches()

                await session.commit()
                return {"success": True, "closed_count": closed_count}
        finally:
            await db_helper.dispose()

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
        redis = RedisService()
        try:
            async with db_helper.session_factory() as session:
                batch_repo = BatchRepository(session)

                stats_data = await batch_repo.update_cached_statistics()

                await redis.set_cache("dashboard_stats", stats_data, 300)

                return {"success": True, "stats": stats_data}
        finally:
            await db_helper.dispose()
            await redis.close()

    return asyncio.run(_logic())


@celery_app.task
def retry_failed_webhooks():
    async def _logic():
        try:
            async with db_helper.session_factory() as session:
                webhook_repo = WebhookRepository(session)
                deliveries_list = await webhook_repo.get_deliveries_for_retry()

                for delivery in deliveries_list:
                    send_webhook_delivery.delay(delivery.id)

                return {"enqueued_retries": len(deliveries_list)}
        finally:
            await db_helper.dispose()

    return asyncio.run(_logic())
