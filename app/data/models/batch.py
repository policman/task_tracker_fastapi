from datetime import datetime, date

from .types import int_pk, created_at_type, updated_at_type
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, ForeignKey, text, Date, Index, UniqueConstraint

class Batch(Base):
    __tablename__ = 'batches'

    id: Mapped[int_pk]
    is_closed: Mapped[bool] = mapped_column(server_default=text("false"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    task_description: Mapped[str]
    work_center_id: Mapped[int] = mapped_column(ForeignKey('work_centers.id'))
    shift: Mapped[str]
    team: Mapped[str]
    batch_number: Mapped[int] = mapped_column(index=True)
    batch_date: Mapped[date] = mapped_column(Date)
    nomenclature: Mapped[str]
    ekn_code: Mapped[str]
    shift_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    shift_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]

    work_center: Mapped["WorkCenter"] = relationship(back_populates="batches")
    products: Mapped[list["Product"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint('batch_number', 'batch_date', name='uq_batch_number_date'),
        Index('idx_batch_closed', 'is_closed'),
        Index('idx_batch_shift_times', 'shift_start', 'shift_end')
    )