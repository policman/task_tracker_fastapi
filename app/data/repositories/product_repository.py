from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from app.data.models import Product
from typing import Any
from datetime import datetime, UTC

from app.core.cache import redis_service


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_products(self, products: list[dict]) -> list[Product]:
        new_products = [Product(**product) for product in products]

        self.session.add_all(new_products)
        await self.session.commit()

        for product in new_products:
            await self.session.refresh(product)

        return new_products


    async def aggregate_products_batch(
            self,
            batch_id: int,
            unique_codes: list[str]
    ) -> dict[str, Any]:
        found_products = (
            await self.session.scalars(
                select(Product)
                .where(
                    Product.unique_code.in_(unique_codes),
                    Product.batch_id == batch_id,
                )
        )).all()

        found_codes = {p.unique_code for p in found_products}
        already_aggregated_codes = [p.unique_code for p in found_products if p.is_aggregated]
        codes_to_update = [p.unique_code for p in found_products if not p.is_aggregated]
        errors = []

        missing_codes = set(unique_codes) - found_codes
        for code in missing_codes:
            errors.append({"code": code, "reason": "not found in this batch"})

        for code in already_aggregated_codes:
            errors.append({"code": code, "reason": "already aggregated"})

        aggregated_count = 0
        if codes_to_update:
            await self.session.execute(
                update(Product)
                .where(
                    Product.batch_id == batch_id,
                    Product.unique_code.in_(codes_to_update)
                )
                .values(
                    is_aggregated=True,
                    aggregated_at=datetime.now(UTC),
                )
            )
            aggregated_count = len(codes_to_update)
            await self.session.commit()

            await redis_service.delete("dashboard_stats")
            await redis_service.delete(f"batch_detail:batch_id_{batch_id}")
            await redis_service.delete(f"batch_statistics:batch_id_{batch_id}")

        return {
            "success": len(errors) == 0,
            "total": len(unique_codes),
            "aggregated": aggregated_count,
            "failed": len(errors),
            "errors": errors,
        }

    async def get_batch_with_products(self, batch_id: int) -> list[Product]:
        return list((await self.session.scalars(
            select(Product)
            .where(Product.batch_id == batch_id)
        )).all())