from http.client import HTTPException

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas.batch import BatchFilter
from api.v1.schemas.product import ProductResponse, ProductCreate, AggregateProductRequest
from app.api.v1.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.data.repositories.batch_repository import BatchRepository
from app.core.database import db_helper
from data.repositories.product_repository import ProductRepository

router = APIRouter(prefix="/batches", tags=["Batches"])


# В ТЗ клиент присылает массив партий, поэтому принимаем List[BatchCreate]
@router.post("", response_model=list[BatchResponse], status_code=201)
async def create_batches(
    batches_in: list[BatchCreate],
    session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = BatchRepository(session)
    created_batches = []

    for batch_pydantic in batches_in:
        batch_dict = batch_pydantic.model_dump()
        new_batch = await repo.create_batch(batch_dict)
        created_batches.append(new_batch)

    return created_batches


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = BatchRepository(session)
    batch = await repo.get_batch(batch_id)

    if not batch:
        raise HTTPException(
            status_code=404,
            detail=f"Batch with ID {batch_id} not found"
        )

    return batch


@router.get("", response_model=list[BatchResponse])
async def get_filtered_batches(
        filters: BatchFilter = Depends(),
        session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = BatchRepository(session)

    filter_dict = filters.model_dump(exclude_none=True)

    filtered_batches = await repo.get_filtered_batch(filter_dict)

    return filtered_batches


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: int,
    update_schema: BatchUpdate,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = BatchRepository(session)

    update_dict = update_schema.model_dump(exclude_unset=True)

    if update_dict is None:
        return await repo.get_batch(batch_id)

    updated_batch = await repo.update_batch(batch_id, update_dict)

    if not updated_batch:
        raise HTTPException(
            status_code=404,
            detail=f"Batch with ID {batch_id} not found"
        )

    return updated_batch

@router.post("/{batch_id}/aggregate")
async def aggregate_product (
    batch_id: int,
    payload: AggregateProductRequest,
    session: AsyncSession = Depends(db_helper.session_getter)
) -> dict:
    repo = ProductRepository(session)

    updated_count = await repo.aggregate_products(batch_id, payload.unique_codes)

    if updated_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No products were aggregated. Check unique_codes or batch_id."
        )

    return {"message": f"Successfully aggregated {updated_count} products."}










