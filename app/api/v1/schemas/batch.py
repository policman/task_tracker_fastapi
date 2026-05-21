from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from .product import ProductResponse

class BatchCreate(BaseModel):
    is_closed: bool = Field(alias="СтатусЗакрытия", default=False)
    task_description: str = Field(alias="ПредставлениеЗаданияНаСмену")
    work_center_name: str = Field(alias="РабочийЦентр")
    shift: str = Field(alias="Смена")
    team: str = Field(alias="Бригада")
    batch_number: int = Field(alias="НомерПартии")
    batch_date: date = Field(alias="ДатаПартии")
    nomenclature: str = Field(alias="Номенклатура")
    ekn_code: str = Field(alias="КодЕКН")
    work_center_identifier: str = Field(alias="ИдентификаторРЦ")
    shift_start: datetime = Field(alias="ДатаВремяНачалаСмены")
    shift_end: datetime = Field(alias="ДатаВремяОкончанияСмены")

    model_config = ConfigDict(populate_by_name=True)

class BatchUpdate(BaseModel):
    is_closed: bool | None = None

class BatchResponse(BaseModel):
    id: int
    is_closed: bool
    batch_number: int
    batch_date: date
    products: list[ProductResponse] = []

    model_config = ConfigDict(from_attributes=True)

class BatchExportFilter(BaseModel):
    is_closed: bool | None = None
    date_from: date | None = None
    date_to: date | None = None

class BatchFilter(BaseModel):
    is_closed: bool | None = None
    batch_number: int | None = None
    batch_date: date | None = None
    work_center_id: str | None = None
    shift: str | None = None

    offset: int = Field(default=0)
    limit: int = Field(default=20, ge=1, le=100)

class ReportRequestSchema(BaseModel):
    format: str = "excel"
    email: EmailStr | None = None

class BatchExportFilters(BaseModel):
    is_closed: bool | None = None
    date_from: date | None = None
    date_to: date | None = None


