import asyncio
from datetime import datetime, UTC

from app.celery_app import celery_app
from app.core.database import DatabaseHelper
from app.data.repositories.product_repository import ProductRepository
from app.core.config import settings
from app.core.cache import RedisService
from app.domain.services.webhook_service import WebhookService


@celery_app.task(bind=True, max_retries=3)
def aggregate_products_batch(
    self, batch_id: int, unique_codes: list[str], user_id: int | None = None
):
    self.update_state(
        state="PROGRESS",
        meta={
            "current": 0,
            "total": len(unique_codes),
            "progress": 0,
        },
    )

    async def _logic():
        local_db = DatabaseHelper(database_url=settings.database_url, echo=False)
        local_redis = RedisService()
        try:
            async with local_db.session_factory() as session:
                product_repo = ProductRepository(session)
                webhook_service = WebhookService(session)

                result = await product_repo.aggregate_products_batch(batch_id, unique_codes)

                if result["aggregated"] > 0:
                    await webhook_service.trigger_product_aggregated(
                        unique_codes=result["updated_codes"],
                        batch_id=batch_id,
                        aggregated_at=datetime.now(UTC),
                    )

                await session.commit()

                await local_redis.delete("dashboard_stats")
                await local_redis.delete(f"batch_detail:batch_id_{batch_id}")
                await local_redis.delete(f"batch_statistics:batch_id_{batch_id}")

                return result
        finally:
            await local_db.dispose()
            await local_redis.close()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        raise self.retry(exc=e, countdown=5)
