from datetime import datetime
from typing import Annotated
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime, func

int_pk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
created_at_type = Annotated[datetime, mapped_column(
    DateTime(timezone=True),
    server_default=func.now()
)]
updated_at_type = Annotated[datetime | None, mapped_column(
    DateTime(timezone=True),
    onupdate=func.now()
)]
