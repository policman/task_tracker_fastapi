import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.v1.schemas.batch import (
    BatchBulkCreate,
    BatchExportRequest,
    BatchFilter,
    BatchResponse,
    BatchResponseList,
    BatchUpdate,
    BatchWithProductsResponse,
    ExtendedBatchStatisticsResponse,
    ReportRequestSchema,
)
from app.api.v1.schemas.product import AggregateProductsRequest
from app.core.cache import cached
from app.core.config import settings
from app.core.dependencies import get_batch_service, get_product_service
from app.core.exceptions import BusinessLogicException
from app.domain.services.batch_service import BatchService
from app.domain.services.product_service import ProductService
from app.storage.minio_service import storage_service
from app.tasks.aggregation import aggregate_batch_products
from app.tasks.exports import export_batches_to_file
from app.tasks.imports import import_batches_from_file
from app.tasks.reports import generate_batch_report

router = APIRouter(prefix="/api/v1/batches", tags=["Batches"])


@router.post("", response_model=BatchResponseList, status_code=status.HTTP_201_CREATED)
async def create_batches(
    payload: BatchBulkCreate,
    batch_service: BatchService = Depends(get_batch_service),
):
    batches_data = [batch.model_dump() for batch in payload.batches]
    created_batches = await batch_service.bulk_create_batches(batches_data)

    return BatchResponseList(batches=created_batches)


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    batch_service: BatchService = Depends(get_batch_service),
):
    return await batch_service.get_batch(batch_id)


@router.get("/{batch_id}/products", response_model=BatchWithProductsResponse)
@cached(ttl=600, key_prefix="batch_detail")
async def get_batch_with_products(
    batch_id: int,
    batch_service: BatchService = Depends(get_batch_service),
):
    return await batch_service.get_batch_with_products(batch_id)


@router.get("", response_model=BatchResponseList)
@cached(ttl=60, key_prefix="batches_filtered_list")
async def get_batches_list(
    filters: BatchFilter = Depends(),
    batch_service: BatchService = Depends(get_batch_service),
):
    batches = await batch_service.get_filtered_batch(
        filters.model_dump(exclude_none=True)
    )
    return {"batches": batches}


@router.get("/{batch_id}/statistics", response_model=ExtendedBatchStatisticsResponse)
@cached(ttl=300, key_prefix="batch_statistics")
async def get_batch_statistics(
    batch_id: int,
    batch_service: BatchService = Depends(get_batch_service),
):
    return await batch_service.get_batch_statistics(batch_id)


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: int,
    update_schema: BatchUpdate,
    batch_service: BatchService = Depends(get_batch_service),
):
    update_dict = update_schema.model_dump(exclude_unset=True)
    return await batch_service.update_batch(batch_id, update_dict)


@router.post("/{batch_id}/aggregate")
async def aggregate_products(
    batch_id: int,
    payload: AggregateProductsRequest,
    product_service: ProductService = Depends(get_product_service),
) -> dict:
    return await product_service.aggregate_batch_products(
        batch_id, payload.unique_codes
    )


@router.post("/{batch_id}/aggregate-async", status_code=status.HTTP_202_ACCEPTED)
def aggregate_products_async(
    batch_id: int, products_list: AggregateProductsRequest
) -> dict:
    task = aggregate_batch_products.delay(batch_id, products_list.unique_codes)

    return {
        "task_id": task.id,
        "status": "PENDING",
        "message": "Aggregation task started in background",
    }


@router.post("/{batch_id}/reports", status_code=status.HTTP_202_ACCEPTED)
def batch_generate_report(batch_id: int, payload: ReportRequestSchema):
    task = generate_batch_report.delay(batch_id, payload.format, payload.email)

    return {
        "task_id": task.id,
        "status": "PENDING",
        "message": "Report generation task started",
    }


@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
def import_batches(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1]

    if ext not in ["csv", "xlsx"]:
        raise BusinessLogicException(message="Only .csv and .xlsx files allowed")

    object_name = f"import_{uuid.uuid4().hex}.{ext}"

    try:
        storage_service.upload_stream(
            bucket=settings.minio.bucket_imports,
            object_name=object_name,
            file_data=file.file,
            length=file.size,
        )
    except Exception as e:
        raise e

    task = import_batches_from_file.delay(object_name)

    return {
        "task_id": task.id,
        "status": "PENDING",
        "message": "File uploaded, import started",
    }


@router.post("/export", status_code=status.HTTP_202_ACCEPTED)
def export_batches(payload: BatchExportRequest):
    task = export_batches_to_file.delay(
        payload.filters.model_dump(exclude_none=True), payload.format_file
    )

    return {"task_id": task.id}
