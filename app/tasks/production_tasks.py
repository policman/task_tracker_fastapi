import asyncio
from app.celery_app import celery_app
from app.core.database import db_helper
from app.data.repositories.product_repository import ProductRepository


@celery_app.task(bind=True, name="aggregate_products_batch")
def aggregate_products_batch(self, batch_id: int, unique_codes: list[str]):
    async def _aggregate_logic():
        async with db_helper.session_factory() as session:
            repo = ProductRepository(session)
            updated_count = await repo.aggregate_products(batch_id, unique_codes)

            total_requested = len(unique_codes)
            return {
                "success": True,
                "total": total_requested,
                "aggregated": updated_count,
                "failed": total_requested - updated_count,
            }

    return asyncio.run(_aggregate_logic())