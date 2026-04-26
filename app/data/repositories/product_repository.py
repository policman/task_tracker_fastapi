from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.data.models import Product

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

    async def aggregate_products(self, batch_id: int, unique_codes: list[str]) -> int:
        result = await self.session.execute(
            update(Product)
            .where(
                Product.batch_id == batch_id,
                Product.unique_code.in_(unique_codes),
                Product.is_aggregated.is_(False)
            )
            .values(is_aggregated=True)
        )
        await self.session.commit()

        return result.rowcount

    async def get_batch_products(self, batch_id: int) -> list[Product]:
        result = await self.session.scalars(
            select(Product)
            .where(Product.batch_id == batch_id)
        )
        return list(result.all())



