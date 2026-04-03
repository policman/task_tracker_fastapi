import enum
from sqlalchemy import ForeignKey, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


# Определяем статусы партии через Enum
class BatchStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Batch(TimestampMixin, Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    batch_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus), default=BatchStatus.PLANNED
    )

    # Внешний ключ на таблицу products
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    # Связь с продуктом
    product = relationship("Product", back_populates="batches")