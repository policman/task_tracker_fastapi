from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from datetime import datetime
from typing import Any, Literal

EventType = Literal[
    "batch_created",
    "batch_updated",
    "batch_closed",
    "product_aggregated",
    "report_generated",
    "import_completed"
]

class WebhookSubscriptionCreate(BaseModel):
    url: HttpUrl
    events: list[EventType] = Field(min_length=1)
    secret_key: str = Field(min_length=8)
    retry_count: int = Field(default=3, ge=0, le=5)
    timeout: int = Field(default=10, ge=1, le=30)

class WebhookSubscriptionUpdate(BaseModel):
    is_active: bool | None = None
    events: list[EventType] | None = None

class WebhookSubscriptionResponse(BaseModel):
    id: int
    url: HttpUrl
    events: list[str]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WebhookDeliveryResponse(BaseModel):
    id: int
    event_type: str
    status: str
    attempts: int
    response_status: int | None = None
    error_message: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)