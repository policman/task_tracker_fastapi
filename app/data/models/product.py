from datetime import datetime

from .base import Base
from sqlalchemy import ForeignKey, Index, text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .types import int_pk, created_at_type

class Product(Base):
    __tablename__ = 'products'

    id: Mapped[int_pk]
    unique_code: Mapped[str] = mapped_column(unique=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), index=True)
    is_aggregated: Mapped[bool] = mapped_column(server_default=text("false"), index=True)
    aggregated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[created_at_type]

    batch: Mapped["Batch"] = relationship(back_populates="products")

    __table_args__ = (
        Index('idx_product_batch_aggregated', 'batch_id', 'is_aggregated'),
    )