import asyncio

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import DatabaseHelper
from app.domain.services.webhook_service import WebhookService


@celery_app.task(
    bind=True,
    name="send_webhook_delivery_task",
    retry_backoff=True,
    retry_backoff_max=60,
)
def send_webhook_delivery(self, delivery_id: int):
    retry_exc = None
    retry_countdown = 60

    async def _logic():
        nonlocal retry_exc, retry_countdown
        local_db = DatabaseHelper(database_url=settings.database_url, echo=False)

        try:
            async with local_db.session_factory() as session:
                service = WebhookService(session)
                result = await service.process_delivery(delivery_id)

                if result.get("error") == "not_found_in_db":
                    retry_exc = result["retry_exc"]
                    retry_countdown = 2
                    return {"success": False}

                if result.get("retry_exc"):
                    retry_exc = result["retry_exc"]
                    retry_countdown = 60 * result.get("attempts", 1)

                return {"success": result["success"], "delivery_id": delivery_id}

        finally:
            await local_db.dispose()

    result = asyncio.run(_logic())

    if retry_exc:
        raise self.retry(exc=retry_exc, countdown=retry_countdown, max_retries=10)

    return result
