from datetime import UTC, datetime
from logging import getLogger
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.task import ProductReportData, ProductsReportData
from app.core.exceptions import BusinessLogicException, NotFoundException
from app.data.repositories.product_repository import ProductRepository
from app.domain.services.webhook_service import WebhookService

logger = getLogger(__name__)


class ProductService:
    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.webhook_service = WebhookService(session)

        from app.core.cache import redis_service as global_redis

        self.redis_client = redis_client or global_redis

    async def create_products(self, products_data: list[dict]):
        try:
            created_products = await self.product_repo.create_products(products_data)
            await self.session.commit()
            logger.info(f"Success created {len(created_products)} products")

        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(
                f"Database integrity error during product creation: {str(e)}"
            )
            raise NotFoundException(message="Batch for creating product(s) not found")

        await self.redis_client.delete("dashboard_stats")

        unique_batch_ids = {
            product.batch_id for product in created_products if product.batch_id
        }

        for batch_id in unique_batch_ids:
            await self.redis_client.delete(f"batch_detail:batch_id_{batch_id}")
            await self.redis_client.delete(f"batch_statistics:batch_id_{batch_id}")
            logger.debug(f"Cache for batch {batch_id} cleared")

        return created_products

    async def products_report_data(self, batch_id: int) -> ProductsReportData:
        products = await self.product_repo.get_batch_with_products(batch_id)
        return ProductsReportData(
            products=[ProductReportData.model_validate(p) for p in products]
        )

    async def aggregate_batch_products(
        self, batch_id: int, unique_codes: list[str]
    ) -> dict[str, Any]:
        found_products = await self.product_repo.get_products_to_aggregate(
            batch_id, unique_codes
        )
        if not found_products:
            raise BusinessLogicException("No products to aggregate")

        found_codes = {p.unique_code for p in found_products}
        already_aggregated_codes = [
            p.unique_code for p in found_products if p.is_aggregated
        ]
        codes_to_update = [p.unique_code for p in found_products if not p.is_aggregated]
        errors = []

        missing_codes = set(unique_codes) - found_codes
        for code in missing_codes:
            errors.append({"code": code, "reason": "not found in this batch"})

        for code in already_aggregated_codes:
            errors.append({"code": code, "reason": "already aggregated"})

        aggregated_count = 0
        if codes_to_update:
            aggregated_count = await self.product_repo.aggregate_products_batch(
                batch_id, codes_to_update
            )

        if aggregated_count == 0:
            raise BusinessLogicException(
                message="No one products was aggregated", payload={"errors": errors}
            )

        await self.session.commit()

        await self.webhook_service.trigger_product_aggregated(
            unique_codes=codes_to_update,
            batch_id=batch_id,
            aggregated_at=datetime.now(UTC),
        )

        await self.redis_client.delete("dashboard_stats")
        await self.redis_client.delete(f"batch_detail:batch_id_{batch_id}")
        await self.redis_client.delete(f"batch_statistics:batch_id_{batch_id}")

        return {
            "success": len(errors) == 0,
            "total": len(unique_codes),
            "aggregated": aggregated_count,
            "failed": len(errors),
            "errors": errors,
            "updated_codes": codes_to_update,
        }
