import asyncio

from app.celery_app import celery_app
from app.core.cache import RedisService
from app.core.config import settings
from app.core.database import DatabaseHelper
from app.core.exceptions import BusinessLogicException
from app.domain.services.product_service import ProductService


@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    name="aggregate_batch_products_task",
)
def aggregate_batch_products(
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
                product_service = ProductService(session, redis_client=local_redis)
                return await product_service.aggregate_batch_products(
                    batch_id, unique_codes
                )
        finally:
            await local_db.dispose()
            await local_redis.close()

    try:
        return asyncio.run(_logic())
    except BusinessLogicException as e:
        return {"success": False, "message": e.message, "errors": e.payload}
    except Exception as e:
        raise self.retry(exc=e, countdown=5)
