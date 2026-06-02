from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.task import ProductReportData, ProductsReportData
from app.data.repositories.product_repository import ProductRepository


async def products_report_data(session: AsyncSession, batch_id: int) -> ProductsReportData:
    repo = ProductRepository(session)
    products = await repo.get_batch_with_products(batch_id)

    return ProductsReportData(products=[ProductReportData.model_validate(p) for p in products])
