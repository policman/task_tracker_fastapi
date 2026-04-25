from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_helper
from api.v1.schemas.product import ProductResponse, ProductCreate
from app.data.repositories.product_repository import ProductRepository

router = APIRouter(prefix="/products", tags=["products"])

@router.post("", response_model=list[ProductResponse], status_code=201)
async def create_products(
    products_in: list[ProductCreate],
    session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = ProductRepository(session)

    products_dict_list = [product.model_dump() for product in products_in]

    created_products = await repo.create_products(products_dict_list)

    return created_products


#TODO: сделать репо для create_product и ручки 5, 6
# проверить работоспособность
# закомитить изменения


#TODO: разобраться с celery