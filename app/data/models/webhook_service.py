from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, JSON, ForeignKey, String, text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .types import created_at_type, int_pk, updated_at_type


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[int_pk]
    url: Mapped[str]
    events: Mapped[list[str]] = mapped_column(ARRAY(String))
    secret_key: Mapped[str]
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    retry_count: Mapped[int] = mapped_column(server_default=text("3"))
    timeout: Mapped[int] = mapped_column(server_default=text("10"))

    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[int_pk]
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE")
    )
    event_type: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str]
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    response_status: Mapped[int | None]
    response_body: Mapped[str | None]
    error_message: Mapped[str | None]

    created_at: Mapped[created_at_type]
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subscription: Mapped["WebhookSubscription"] = relationship(back_populates="deliveries")
