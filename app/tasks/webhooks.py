import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.celery_app import celery_app
from app.core.database import DatabaseHelper
from app.data.models.webhook_service import WebhookDelivery


@celery_app.task(bind=True, name="send_webhook_delivery")
def send_webhook_delivery(self, delivery_id: int):
    retry_exc = None
    retry_countdown = 60

    async def _logic():
        nonlocal retry_exc, retry_countdown
        local_db = DatabaseHelper(database_url=settings.database_url, echo=False)

        try:
            async with local_db.session_factory() as session:
                delivery = (
                    await session.scalars(
                        select(WebhookDelivery)
                        .options(selectinload(WebhookDelivery.subscription))
                        .where(WebhookDelivery.id == delivery_id)
                    )
                ).first()

                if not delivery:
                    print(f"Delivery {delivery_id} not found.")
                    raise self.retry(
                        exc=Exception(f"Delivery {delivery_id} not found in DB yet (waiting for commit)"),
                        countdown=2,
                        max_retries=5
                    )
                elif not delivery.subscription:
                    print(f"Subscription for delivery {delivery_id} not found.")
                    return {"success": False, "error": "Subscription not found"}

                sub = delivery.subscription

                delivery.attempts += 1

                payload_bytes = json.dumps(delivery.payload, separators=(",", ":")).encode("utf-8")

                signature = hmac.new(
                    key=sub.secret_key.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,  # Тот самый заголовок для верификации
                }

                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            url=sub.url, content=payload_bytes, headers=headers, timeout=sub.timeout
                        )
                        response.raise_for_status()

                    delivery.status = "success"
                    delivery.response_status = response.status_code
                    delivery.response_body = response.text[:500]
                    delivery.error_message = None
                    delivery.delivered_at = datetime.now(UTC)

                    await session.commit()
                    return {"success": True, "delivery_id": delivery_id}

                except httpx.HTTPError as e:
                    delivery.status = "failed"
                    delivery.error_message = str(e)

                    if hasattr(e, "response") and e.response:
                        delivery.response_status = e.response.status_code
                        delivery.response_body = e.response.text[:500]

                    await session.commit()

                    if delivery.attempts < sub.retry_count:
                        retry_exc = e
                        retry_countdown = 60 * delivery.attempts

                    return {"success": False, "delivery_id": delivery_id}

        finally:
            await local_db.dispose()

    asyncio.run(_logic())

    if retry_exc:
        raise self.retry(exc=retry_exc, countdown=retry_countdown, max_retries=10)
