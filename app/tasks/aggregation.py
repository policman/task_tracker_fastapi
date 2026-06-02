import asyncio

from app.celery_app import celery_app
from app.core.database import db_helper
from app.data.repositories.product_repository import ProductRepository


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
        try:
            async with db_helper.session_factory() as session:
                product_repo = ProductRepository(session)
                result = await product_repo.aggregate_products_batch(batch_id, unique_codes)
                return result
        finally:
            await db_helper.dispose()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        raise self.retry(exc=e, countdown=5)
