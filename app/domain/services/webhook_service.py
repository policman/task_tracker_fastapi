import hashlib
import hmac
import json
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from app.core.exceptions import BusinessLogicException, NotFoundException
from app.data.models.webhook_service import WebhookDelivery, WebhookSubscription
from app.data.repositories.webhook_repository import WebhookRepository


class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.webhook_repo = WebhookRepository(session)

    async def create_subscription(self, data: dict) -> WebhookSubscription:
        if "url" in data and data["url"]:
            data["url"] = str(data["url"])

        new_subscription = await self.webhook_repo.create(data)
        await self.session.commit()

        return new_subscription

    async def get_subscriptions(self) -> list[WebhookSubscription]:
        return await self.webhook_repo.get_subscriptions()

    async def update_subscription(
        self, webhook_id: int, update_data: dict
    ) -> WebhookSubscription:
        if not update_data:
            raise BusinessLogicException(message="No fields to update")

        updated_sub = await self.webhook_repo.update_subscription(
            webhook_id, update_data
        )

        if not updated_sub:
            raise NotFoundException(message="Subscription not found")

        await self.session.commit()
        return updated_sub

    async def delete_subscription(self, webhook_id: int) -> None:
        await self.webhook_repo.delete_subscription(webhook_id)
        await self.session.commit()

    async def get_webhook_deliveries(
        self, webhook_id: int, limit: int = 20, offset: int = 0
    ):
        return await self.webhook_repo.get_deliveries(webhook_id, limit, offset)

    async def _trigger_event(self, event_type: str, data: BaseModel):
        event_payload = BaseWebhookEvent(
            event=event_type,
            timestamp=datetime.now(UTC),
            data=data.model_dump(mode="json"),
        ).model_dump(mode="json")

        stmt = select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True),
            WebhookSubscription.events.any(event_type),
        )
        subscribers = (await self.session.scalars(stmt)).all()

        if not subscribers:
            return

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

        from app.tasks.webhooks import send_webhook_delivery

        for delivery in deliveries:
            send_webhook_delivery.apply_async(args=[delivery.id], countdown=2)

    async def _trigger_events_bulk(self, event_type: str, events_data: list[BaseModel]):
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True),
            WebhookSubscription.events.any(event_type),
        )
        subscribers = (await self.session.scalars(stmt)).all()

        if not subscribers:
            return

        deliveries = []
        for data in events_data:
            event_payload = BaseWebhookEvent(
                event=event_type,
                timestamp=datetime.now(UTC),
                data=data.model_dump(mode="json"),
            ).model_dump(mode="json")

            for sub in subscribers:
                delivery = WebhookDelivery(
                    subscription_id=sub.id,
                    event_type=event_type,
                    payload=event_payload,
                    status="pending",
                )
                deliveries.append(delivery)

        self.session.add_all(deliveries)
        await self.session.flush()

        from app.tasks.webhooks import send_webhook_delivery

        for delivery in deliveries:
            send_webhook_delivery.apply_async(args=[delivery.id], countdown=2)

    async def trigger_batches_created_bulk(self, batches: list):
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

    async def trigger_batch_updated(
        self, batch_id: int, batch_number: str | int, changes: dict
    ):
        data = BatchUpdatedData(id=batch_id, batch_number=batch_number, changes=changes)
        await self._trigger_event("batch_updated", data)

    async def trigger_batch_closed(
        self,
        batch_id: int,
        batch_number: str | int,
        closed_at: datetime,
        statistics: dict,
    ):
        data = BatchClosedData(
            id=batch_id,
            batch_number=batch_number,
            closed_at=closed_at,
            statistics=statistics,
        )
        await self._trigger_event("batch_closed", data)

    async def trigger_product_aggregated(
        self, unique_codes: list[str], batch_id: int, aggregated_at: datetime
    ):
        data = ProductAggregatedData(
            unique_codes=unique_codes,
            batch_id=batch_id,
            aggregated_at=aggregated_at,
        )
        await self._trigger_event("product_aggregated", data)

    async def trigger_report_generated(
        self, batch_id: int, report_type: str, file_url: str
    ):
        data = ReportGeneratedData(
            batch_id=batch_id, report_type=report_type, file_url=file_url
        )
        await self._trigger_event("report_generated", data)

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

    async def get_deliveries_for_retry(self) -> list[WebhookDelivery]:
        return await self.webhook_repo.get_deliveries_for_retry()

    async def process_delivery(self, delivery_id: int) -> dict:
        delivery = (
            await self.session.scalars(
                select(WebhookDelivery)
                .options(selectinload(WebhookDelivery.subscription))
                .where(WebhookDelivery.id == delivery_id)
            )
        ).first()

        if not delivery:
            return {
                "success": False,
                "error": "not_found_in_db",
                "retry_exc": Exception("Not found"),
            }

        if not delivery.subscription:
            return {
                "success": False,
                "error": "Subscription not found",
                "retry_exc": None,
            }

        sub = delivery.subscription
        delivery.attempts += 1

        payload_bytes = json.dumps(delivery.payload, separators=(",", ":")).encode(
            "utf-8"
        )

        signature = hmac.new(
            key=sub.secret_key.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=sub.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=sub.timeout,
                )
                response.raise_for_status()

            delivery.status = "success"
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:500]
            delivery.error_message = None
            delivery.delivered_at = datetime.now(UTC)

            await self.session.commit()
            return {"success": True, "retry_exc": None}

        except httpx.HTTPError as e:
            delivery.status = "failed"
            delivery.error_message = str(e)

            if hasattr(e, "response") and e.response:
                delivery.response_status = e.response.status_code
                delivery.response_body = e.response.text[:500]

            await self.session.commit()

            retry_exc = None
            if delivery.attempts < sub.retry_count:
                retry_exc = e

            return {
                "success": False,
                "retry_exc": retry_exc,
                "attempts": delivery.attempts,
            }
