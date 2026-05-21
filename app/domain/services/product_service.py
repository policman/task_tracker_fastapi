from app.api.v1.schemas.task import ProductReportData
from app.api.v1.schemas.task import ProductsReportData
from app.data.repositories.product_repository import ProductRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def products_report_data(session: AsyncSession, batch_id: int) -> ProductsReportData:
    repo = ProductRepository(session)
    products = await repo.get_batch_products(batch_id)

    return ProductsReportData(products=[ProductReportData.model_validate(p) for p in products])