from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.models.webhook_service import WebhookSubscription, WebhookDelivery

class WebhookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_subscription(self, data: dict) -> WebhookSubscription:
        new_sub = WebhookSubscription(**data)
        self.session.add(new_sub)
        await self.session.flush()
        return new_sub

    async def get_subscriptions(self) -> list[WebhookSubscription]:
        subs = await self.session.scalars(select(WebhookSubscription))
        return list(subs.all())

    async def update_subscription(self, webhook_id: int, data: dict) -> WebhookSubscription | None:

        updated_sub = await self.session.scalars(
            update(WebhookSubscription)
            .where(WebhookSubscription.id == webhook_id)
            .values(**data)
            .returning(WebhookSubscription)
        )
        return updated_sub.first()

    async def delete_subscription(self, webhook_id: int) -> None:
        await self.session.execute(
            delete(WebhookSubscription)
            .where(WebhookSubscription.id == webhook_id)
        )

    async def get_deliveries(self, webhook_id: int, limit: int = 20, offset: int = 0) -> list[WebhookDelivery]:
        deliveries = await self.session.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(deliveries.all())

    async def get_deliveries_for_retry(self) -> list[WebhookDelivery]:
        dels_for_retry = await self.session.scalars(
            select(WebhookDelivery)
            .join(WebhookSubscription, WebhookSubscription.id == WebhookDelivery.subscription_id)
            .where(
                WebhookDelivery.status == 'failed',
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
                WebhookSubscription.is_active.is_(True)
            )
        )
        return list(dels_for_retry.all())
