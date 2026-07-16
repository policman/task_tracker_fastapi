from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_batches: int
    active_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int
    aggregation_rate: float


class DashboardToday(BaseModel):
    batches_created: int
    batches_closed: int
    products_added: int
    products_aggregated: int


class ShiftStats(BaseModel):
    batches: int
    products: int
    aggregated: int


class TopWorkCenter(BaseModel):
    id: str
    name: str
    batches_count: int
    products_count: int
    aggregation_rate: float


class DashboardStatisticsResponse(BaseModel):
    summary: DashboardSummary
    today: DashboardToday
    by_shift: dict[str, ShiftStats]
    top_work_centers: list[TopWorkCenter]
    cached_at: datetime


class CompareBatchesRequest(BaseModel):
    batch_ids: list[int]


class BatchComparison(BaseModel):
    batch_id: int
    batch_number: str | int
    total_products: int
    aggregated: int
    rate: float
    duration_hours: float
    products_per_hour: float


class AverageComparison(BaseModel):
    aggregation_rate: float
    products_per_hour: float


class CompareBatchesResponse(BaseModel):
    comparison: list[BatchComparison]
    average: AverageComparison
