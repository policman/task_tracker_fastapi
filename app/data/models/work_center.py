from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .types import created_at_type, int_pk, updated_at_type


class WorkCenter(Base):
    __tablename__ = "work_centers"

    id: Mapped[int_pk]
    identifier: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]

    batches: Mapped[list["Batch"]] = relationship(
        back_populates="work_center",
        cascade="all, delete, delete-orphan",
    )
