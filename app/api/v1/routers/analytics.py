from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.common import DashboardStatisticsResponse
from app.core.cache import cached
from app.core.database import db_helper
from app.data.repositories.batch_repository import BatchRepository

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStatisticsResponse)
@cached(ttl=15, key_prefix="dashboard_stats")
async def get_dashboard_statistics(session: AsyncSession = Depends(db_helper.session_getter)):
    """
    Return result for dashboard statistics
    Cache in 5 minutes
    """
    repo = BatchRepository(session)
    return await repo.update_cached_statistics()
