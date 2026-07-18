from fastapi import APIRouter, Depends, status

from app.api.v1.schemas.product import ProductCreate, ProductResponse
from app.core.dependencies import get_product_service
from app.domain.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.post(
    "", response_model=list[ProductResponse], status_code=status.HTTP_201_CREATED
)
async def create_products(
    products_in: list[ProductCreate],
    product_service: ProductService = Depends(get_product_service),
):
    products_dict_list = [product.model_dump() for product in products_in]
    return await product_service.create_products(products_dict_list)
