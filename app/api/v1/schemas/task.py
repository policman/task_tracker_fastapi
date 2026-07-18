from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BatchGenerateData(BaseModel):
    batch_number: int = Field(alias="Номер партии")
    batch_date: date = Field(alias="Дата партии")
    is_closed: bool = Field(alias="Статус")
    work_center_id: int = Field(alias="Рабочий центр")
    shift: str = Field(alias="Смена")
    team: str = Field(alias="Бригада")
    shift_start: datetime = Field(alias="Начало смены")
    shift_end: datetime = Field(alias="Окончание смены")
    nomenclature: str = Field(alias="Номенклатура")

    model_config = ConfigDict(populate_by_name=True)


class ProductReportData(BaseModel):
    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductsReportData(BaseModel):
    products: list[ProductReportData]


class StatsReportData(BaseModel):
    total_products: int
    aggregated_products: int
    unaggregated_products: int
    percent_aggregated: float
    avg_speed: float | None = None
