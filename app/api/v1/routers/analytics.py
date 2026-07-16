from fastapi import APIRouter, Depends

from app.api.v1.schemas.common import (
    CompareBatchesRequest,
    CompareBatchesResponse,
    DashboardStatisticsResponse,
)
from app.core.cache import cached
from app.core.dependencies import get_batch_service
from app.domain.services.batch_service import BatchService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardStatisticsResponse)
@cached(ttl=15, key_prefix="dashboard_stats")
async def get_dashboard_statistics(
    batch_service: BatchService = Depends(get_batch_service),
):
    return await batch_service.get_dashboard_statistics()


@router.post("/compare-batches", response_model=CompareBatchesResponse)
async def compare_batches_route(
    payload: CompareBatchesRequest,
    batch_service: BatchService = Depends(get_batch_service),
):
    return await batch_service.compare_batches(payload.batch_ids)
