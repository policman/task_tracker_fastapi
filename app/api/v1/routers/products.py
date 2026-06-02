from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.product import ProductCreate, ProductResponse
from app.core.database import db_helper
from app.data.repositories.product_repository import ProductRepository
from app.core.cache import redis_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=list[ProductResponse], status_code=201)
async def create_products(
    products_in: list[ProductCreate], session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = ProductRepository(session)

    products_dict_list = [product.model_dump() for product in products_in]

    created_products = await repo.create_products(products_dict_list)

    await session.commit()

    await redis_service.delete("dashboard_stats")

    for product in created_products:
        await redis_service.delete(f"batch_detail:batch_id_{product.batch_id}")
        await redis_service.delete(f"batch_statistics:batch_id_{product.batch_id}")

    return created_products
