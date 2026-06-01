from pydantic import BaseModel, ConfigDict, HttpUrl
from datetime import datetime
from typing import Any

# --- Базовая обертка для итогового JSON ---
class BaseWebhookEvent(BaseModel):
    event: str
    timestamp: datetime
    data: dict[str, Any]

# --- 1. batch_created ---
class BatchCreatedData(BaseModel):
    id: int
    batch_number: str | int
    batch_date: str
    nomenclature: str
    work_center: str

# --- 2. batch_updated ---
class BatchUpdatedData(BaseModel):
    id: int
    batch_number: str | int
    changes: dict[str, Any]

# --- 3. batch_closed ---
class BatchClosedData(BaseModel):
    id: int
    batch_number: str | int
    closed_at: datetime
    statistics: dict[str, int | float]

# --- 4. product_aggregated ---
class ProductAggregatedData(BaseModel):
    unique_code: str
    batch_id: int
    batch_number: str | int
    aggregated_at: datetime

# --- 5. report_generated ---
class ReportGeneratedData(BaseModel):
    batch_id: int
    report_type: str
    file_url: str | HttpUrl
    expires_at: datetime

# --- 6. import_completed ---
class ImportErrorDetail(BaseModel):
    row: int
    error: str

class ImportCompletedData(BaseModel):
    total_rows: int
    created: int
    skipped: int
    errors: list[ImportErrorDetail]