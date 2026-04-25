from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ProductCreate(BaseModel):
    unique_code: str
    batch_id: int

class AggregateProductRequest(BaseModel):
    unique_codes: list[str]

class ProductResponse(BaseModel):
    id: int
    unique_code: str
    is_aggregated: bool
    aggregated: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
