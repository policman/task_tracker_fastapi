from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    unique_code: str
    batch_id: int


class AggregateProductsRequest(BaseModel):
    unique_codes: list[str]


class ProductResponse(BaseModel):
    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
