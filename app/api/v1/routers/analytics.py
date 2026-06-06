

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.common import DashboardStatisticsResponse, CompareBatchesRequest, CompareBatchesResponse
from app.core.cache import cached
from app.core.database import db_helper
from app.data.repositories.batch_repository import BatchRepository

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStatisticsResponse)
@cached(ttl=15, key_prefix="dashboard_stats")
async def get_dashboard_statistics(session: AsyncSession = Depends(db_helper.session_getter)):
    repo = BatchRepository(session)
    return await repo.update_cached_statistics()


@router.post("/compare-batches", response_model=CompareBatchesResponse)
async def compare_batches_route(
        payload: CompareBatchesRequest,
        session: AsyncSession = Depends(db_helper.session_getter)
):
    repo = BatchRepository(session)
    comparison_data = await repo.compare_batches(payload.batch_ids)

    if not comparison_data:
        raise HTTPException(status_code=404, detail="No batches found")

    avg_rate = sum(b["rate"] for b in comparison_data) / len(comparison_data)
    avg_speed = sum(b["products_per_hour"] for b in comparison_data) / len(comparison_data)

    return {
        "comparison": comparison_data,
        "average": {
            "aggregation_rate": round(avg_rate, 2),
            "products_per_hour": round(avg_speed, 2)
        }
    }