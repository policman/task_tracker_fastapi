from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import redis_service
from app.data.models import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_products(self, products: list[dict]) -> list[Product]:
        new_products = [Product(**product) for product in products]

        self.session.add_all(new_products)
        await self.session.flush()

        return new_products

    async def get_products_to_aggregate(
        self, batch_id: int, unique_codes: list[str]
    ) -> list[Product]:
        return list(
            (
                await self.session.scalars(
                    select(Product).where(
                        Product.unique_code.in_(unique_codes),
                        Product.batch_id == batch_id,
                    )
                )
            ).all()
        )

    async def aggregate_products_batch(
        self, batch_id: int, unique_codes: list[str]
    ) -> int:
        result = await self.session.execute(
            update(Product)
            .where(Product.batch_id == batch_id, Product.unique_code.in_(unique_codes))
            .values(
                is_aggregated=True,
                aggregated_at=datetime.now(UTC),
            )
        )

        await self.session.flush()

        return result.rowcount

    async def get_batch_with_products(self, batch_id: int) -> list[Product]:
        return list(
            (
                await self.session.scalars(
                    select(Product).where(Product.batch_id == batch_id)
                )
            ).all()
        )
