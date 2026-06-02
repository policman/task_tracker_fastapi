from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.webhook_events import (
    BaseWebhookEvent,
    BatchClosedData,
    BatchCreatedData,
    BatchUpdatedData,
    ImportCompletedData,
    ImportErrorDetail,
    ProductAggregatedData,
    ReportGeneratedData,
)
from app.data.models.webhook_service import WebhookDelivery, WebhookSubscription
from app.tasks.webhooks import send_webhook_delivery


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
            event=event_type, timestamp=datetime.now(UTC), data=data.model_dump(mode="json")
        ).model_dump(mode="json")

        # Ищем активных подписчиков именно на этот event_type
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True), WebhookSubscription.events.any(event_type)
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
                status="pending",
            )
            self.session.add(delivery)
            deliveries.append(delivery)

        await self.session.flush()

        # Ставим задачи в Celery
        for delivery in deliveries:
            send_webhook_delivery.apply_async(args=[delivery.id], countdown=2)

    async def _trigger_events_bulk(self, event_type: str, events_data: list[BaseModel]):
        """
        Оптимизированный метод для массовой отправки.
        Делает SELECT подписчиков только 1 раз.
        """
        # 1. Ищем подписчиков ОДИН раз для всех событий
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True), WebhookSubscription.events.any(event_type)
        )
        subscribers = (await self.session.scalars(stmt)).all()

        if not subscribers:
            return

        # 2. Формируем все доставки в памяти
        deliveries = []
        for data in events_data:
            event_payload = BaseWebhookEvent(
                event=event_type,
                timestamp=datetime.now(UTC),
                data=data.model_dump(mode="json")
            ).model_dump(mode="json")

            for sub in subscribers:
                delivery = WebhookDelivery(
                    subscription_id=sub.id,
                    event_type=event_type,
                    payload=event_payload,
                    status="pending",
                )
                deliveries.append(delivery)

        # 3. Сохраняем все доставки одним запросом
        self.session.add_all(deliveries)
        await self.session.flush()

        # 4. Массово ставим задачи в Celery
        for delivery in deliveries:
            send_webhook_delivery.apply_async(args=[delivery.id], countdown=2)

    async def trigger_batches_created_bulk(self, batches: list):
        """Принимает список созданных объектов Batch"""
        events_data = []
        for batch in batches:
            data = BatchCreatedData(
                id=batch.id,
                batch_number=batch.batch_number,
                batch_date=str(batch.batch_date),
                nomenclature=batch.nomenclature,
                work_center_id=batch.work_center_id,
            )
            events_data.append(data)

        await self._trigger_events_bulk("batch_created", events_data)

    # 1. Партия создана
    async def trigger_batch_created(
        self,
        batch_id: int,
        batch_number: str | int,
        batch_date: str,
        nomenclature: str,
        work_center_id: int,
    ):
        data = BatchCreatedData(
            id=batch_id,
            batch_number=batch_number,
            batch_date=batch_date,
            nomenclature=nomenclature,
            work_center_id=work_center_id,
        )
        await self._trigger_event("batch_created", data)

    # 2. Партия обновлена
    async def trigger_batch_updated(self, batch_id: int, batch_number: str | int, changes: dict):
        data = BatchUpdatedData(id=batch_id, batch_number=batch_number, changes=changes)
        await self._trigger_event("batch_updated", data)

    # 3. Партия закрыта
    async def trigger_batch_closed(
        self, batch_id: int, batch_number: str | int, closed_at: datetime, statistics: dict
    ):
        data = BatchClosedData(
            id=batch_id, batch_number=batch_number, closed_at=closed_at, statistics=statistics
        )
        await self._trigger_event("batch_closed", data)

    # 4. Продукт агрегирован
    async def trigger_product_aggregated(
        self, unique_codes: list[str], batch_id: int, aggregated_at: datetime
    ):
        data = ProductAggregatedData(
            unique_codes=unique_codes,
            batch_id=batch_id,
            aggregated_at=aggregated_at,
        )
        await self._trigger_event("product_aggregated", data)

    # 5. Отчет сгенерирован
    async def trigger_report_generated(
        self, batch_id: int, report_type: str, file_url: str
    ):
        data = ReportGeneratedData(
            batch_id=batch_id, report_type=report_type, file_url=file_url
        )
        await self._trigger_event("report_generated", data)

    # 6. Импорт завершен
    async def trigger_import_completed(
        self, total_rows: int, created: int, skipped: int, errors: list[dict]
    ):
        data = ImportCompletedData(
            total_rows=total_rows,
            created=created,
            skipped=skipped,
            errors=[ImportErrorDetail(**err) for err in errors],
        )
        await self._trigger_event("import_completed", data)
