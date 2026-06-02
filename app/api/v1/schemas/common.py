from datetime import datetime

from pydantic import BaseModel, Field


class DashboardStatisticsResponse(BaseModel):
    total_batches: int = Field(default=0)
    active_batches: int = Field(default=0)
    total_products: int = Field(default=0)
    aggregated_products: int = Field(default=0)
    aggregation_rate: float = Field(default=0.0)
    cached_at: datetime
