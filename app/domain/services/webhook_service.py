from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.data.models.webhook_service import WebhookSubscription, WebhookDelivery
from app.tasks.webhooks import send_webhook_delivery

from app.api.v1.schemas.webhook_events import (
    BaseWebhookEvent,
    BatchCreatedData,
    BatchUpdatedData,
    BatchClosedData,
    ProductAggregatedData,
    ReportGeneratedData,
    ImportCompletedData,
    ImportErrorDetail
)

class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _trigger_event(self, event_type: str, data: BaseModel):
        """
        Внутренний метод: оборачивает данные в итоговый JSON, ищет подписчиков
        и отправляет задания курьеру (Celery).
        """
        # Формируем итоговый payload
        event_payload = BaseWebhookEvent(
            event=event_type,
            timestamp=datetime.now(UTC),
            data=data.model_dump(mode="json")
        ).model_dump(mode="json")

        # Ищем активных подписчиков именно на этот event_type
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True),
            WebhookSubscription.events.any(event_type)
        )
        subscribers = (await self.session.scalars(stmt)).all()

        if not subscribers:
            return

        # Создаем доставки (конверты) в БД
        deliveries = []
        for sub in subscribers:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type=event_type,
                payload=event_payload,
                status="pending"
            )
            self.session.add(delivery)
            deliveries.append(delivery)

        await self.session.flush()

        # Ставим задачи в Celery
        for delivery in deliveries:
            send_webhook_delivery.delay(delivery.id)

    # ==========================================
    # ПУБЛИЧНЫЕ МЕТОДЫ ДЛЯ ВЫЗОВА ИЗ БИЗНЕС-ЛОГИКИ
    # ==========================================

    # 1. Партия создана
    async def trigger_batch_created(self, batch_id: int, batch_number: str | int, batch_date: str, nomenclature: str, work_center: str):
        data = BatchCreatedData(
            id=batch_id,
            batch_number=batch_number,
            batch_date=batch_date,
            nomenclature=nomenclature,
            work_center=work_center
        )
        await self._trigger_event("batch_created", data)

    # 2. Партия обновлена
    async def trigger_batch_updated(self, batch_id: int, batch_number: str | int, changes: dict):
        data = BatchUpdatedData(
            id=batch_id,
            batch_number=batch_number,
            changes=changes
        )
        await self._trigger_event("batch_updated", data)

    # 3. Партия закрыта
    async def trigger_batch_closed(self, batch_id: int, batch_number: str | int, closed_at: datetime, statistics: dict):
        data = BatchClosedData(
            id=batch_id,
            batch_number=batch_number,
            closed_at=closed_at,
            statistics=statistics
        )
        await self._trigger_event("batch_closed", data)

    # 4. Продукт агрегирован
    async def trigger_product_aggregated(self, unique_code: str, batch_id: int, batch_number: str | int, aggregated_at: datetime):
        data = ProductAggregatedData(
            unique_code=unique_code,
            batch_id=batch_id,
            batch_number=batch_number,
            aggregated_at=aggregated_at
        )
        await self._trigger_event("product_aggregated", data)

    # 5. Отчет сгенерирован
    async def trigger_report_generated(self, batch_id: int, report_type: str, file_url: str, expires_at: datetime):
        data = ReportGeneratedData(
            batch_id=batch_id,
            report_type=report_type,
            file_url=file_url,
            expires_at=expires_at
        )
        await self._trigger_event("report_generated", data)

    # 6. Импорт завершен
    async def trigger_import_completed(self, total_rows: int, created: int, skipped: int, errors: list[dict]):
        data = ImportCompletedData(
            total_rows=total_rows,
            created=created,
            skipped=skipped,
            errors=[ImportErrorDetail(**err) for err in errors]
        )
        await self._trigger_event("import_completed", data)