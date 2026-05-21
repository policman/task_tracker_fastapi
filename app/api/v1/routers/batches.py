import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.reports import generate_batch_report
from app.tasks.aggregation import aggregate_products_batch
from app.api.v1.schemas.batch import BatchFilter, BatchExportFilter, ReportRequestSchema
from app.api.v1.schemas.product import ProductResponse, ProductCreate, AggregateProductsRequest
from app.api.v1.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.data.repositories.batch_repository import BatchRepository
from app.core.database import db_helper
from app.data.repositories.product_repository import ProductRepository
from app.core.config import settings
from app.storage.minio_service import storage_service
from app.tasks.imports import import_batches_from_file
from app.tasks.exports import export_batches_to_file

router = APIRouter(prefix="/batches", tags=["Batches"])

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError


@router.post("", response_model=list[BatchResponse], status_code=status.HTTP_201_CREATED)
async def create_batches(
        batches_in: list[BatchCreate],
        session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = BatchRepository(session)
    created_batches = []

    try:
        for batch_pydantic in batches_in:
            # Бизнес-логика: если нужно, проверяем дубликаты тут
            # exists = await repo.exists_by_number_date(...)
            # if exists: raise HTTPException(...)

            batch_dict = batch_pydantic.model_dump()

            # Внутри репо делается flush(), подготавливая SQL-запросы
            new_batch = await repo.create_batch(batch_dict)
            created_batches.append(new_batch)

        # САМОЕ ГЛАВНОЕ: Фиксируем транзакцию!
        # Выполняется ровно ОДИН раз для всего списка.
        await session.commit()

        return created_batches

    except SQLAlchemyError as e:
        # Если хотя бы одна партия вызвала ошибку БД (например, уникальный индекс),
        # мы откатываем ВООБЩЕ ВСЕ добавленные в цикле партии.
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сохранения в БД. Изменения отменены."
        )


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

@router.get("/{batch_id}/products", response_model=list[ProductResponse])
async def get_batch_products(
    batch_id: int,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    batch_repo: BatchRepository = BatchRepository(session)
    batch = await batch_repo.get_batch(batch_id)

    if not batch:
        raise HTTPException(
            status_code=404,
            detail=f"Batch with ID {batch_id} not found"
        )

    product_repo = ProductRepository(session)
    batch_products = await product_repo.get_batch_products(batch_id)

    return batch_products

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
async def aggregate_products(
    batch_id: int,
    payload: AggregateProductsRequest,
    session: AsyncSession = Depends(db_helper.session_getter)
) -> dict:
    repo = ProductRepository(session)

    updated_count = await repo.aggregate_products_batch(batch_id, payload.unique_codes)

    if updated_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No products were aggregated. Check unique_codes or batch_id."
        )

    return {"message": f"Successfully aggregated {updated_count} products."}


@router.post("/{batch_id}/aggregate-async", status_code=status.HTTP_202_ACCEPTED)
def aggregate_products_async(
        batch_id: int,
        products_list: AggregateProductsRequest
):
    task = aggregate_products_batch.delay(batch_id, products_list.unique_codes)

    return {
        "task_id": task.id,
        "status": "PENDING",
        "message": "Aggregation task started in background"
    }


@router.post("/{batch_id}/reports", status_code=status.HTTP_202_ACCEPTED)
async def batch_generate_report(
    batch_id: int,
    payload: ReportRequestSchema
):
    task = generate_batch_report.delay(
        batch_id,
        payload.format,
        payload.email
    )

    return {
        "task_id": task.id,
        "status": "PENDING"
    }

@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_batches(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1]

    if ext not in ["csv", "xlsx"]:
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx files allowed")

    object_name = f"import_{uuid.uuid4().hex}.{ext}"

    try:
        storage_service.upload_stream(
            bucket=settings.minio.bucket_imports,
            object_name=object_name,
            file_data=file.file,
            length=file.size,
            content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")

    task = import_batches_from_file.delay(object_name)

    return {
        "task_id": task.id,
        "status": "PENDING",
        "message": "File uploaded, import started"
    }

@router.post("/export", status_code=status.HTTP_202_ACCEPTED)
async def export_batches(filters: BatchExportFilter, format_file: str = "excel"):
    if format_file not in ["csv", "excel"]:
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx files allowed")

    task = export_batches_to_file.delay(filters.model_dump(exclude_none=True), format_file)

    return {
        "task_id": task.id,
    }



