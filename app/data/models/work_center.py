from .base import Base
from .types import int_pk, created_at_type, updated_at_type
from sqlalchemy.orm import relationship, Mapped, mapped_column

class WorkCenter(Base):
    __tablename__ = 'work_centers'

    id: Mapped[int_pk]
    identifier: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    created_at: Mapped[created_at_type]
    updated_at: Mapped[updated_at_type]

    batches: Mapped[list["Batch"]] = relationship(
        back_populates="work_center",
        cascade="all, delete, delete-orphan",
    )