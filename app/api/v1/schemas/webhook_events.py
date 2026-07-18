from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl


class BaseWebhookEvent(BaseModel):
    event: str
    timestamp: datetime
    data: dict[str, Any]


class BatchCreatedData(BaseModel):
    id: int
    batch_number: str | int
    batch_date: str
    nomenclature: str
    work_center_id: int


class BatchUpdatedData(BaseModel):
    id: int
    batch_number: str | int
    changes: dict[str, Any]


class BatchClosedData(BaseModel):
    id: int
    batch_number: str | int
    closed_at: datetime
    statistics: dict[str, Any]


class ProductAggregatedData(BaseModel):
    unique_codes: list[str]
    batch_id: int
    aggregated_at: datetime


class ReportGeneratedData(BaseModel):
    batch_id: int
    report_type: str
    file_url: str | HttpUrl


class ImportErrorDetail(BaseModel):
    row: int
    error: str


class ImportCompletedData(BaseModel):
    total_rows: int
    created: int
    skipped: int
    errors: list[ImportErrorDetail]
