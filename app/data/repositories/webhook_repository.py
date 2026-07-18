from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models.webhook_service import WebhookDelivery, WebhookSubscription
from app.data.repositories.base_repository import BaseRepository


class WebhookRepository(BaseRepository[WebhookSubscription]):
    def __init__(self, session: AsyncSession):
        self.session = session
        super().__init__(model=WebhookDelivery, session=session)

    async def get_subscriptions(self) -> list[WebhookSubscription]:
        subs = await self.session.scalars(select(self.model))
        return list(subs.all())

    async def update_subscription(
        self, webhook_id: int, data: dict
    ) -> WebhookSubscription | None:
        updated_sub = await self.session.execute(
            update(self.model)
            .where(self.model.id == webhook_id)
            .values(**data)
            .returning(self.model)
        )
        return updated_sub.scalar_one_or_none()

    async def delete_subscription(self, webhook_id: int) -> None:
        await self.session.execute(
            delete(self.model).where(self.model.id == webhook_id)
        )

    async def get_deliveries(
        self, webhook_id: int, limit: int = 20, offset: int = 0
    ) -> list[WebhookDelivery]:
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
            .join(
                WebhookSubscription,
                WebhookSubscription.id == WebhookDelivery.subscription_id,
            )
            .where(
                WebhookDelivery.status == "failed",
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
                WebhookSubscription.is_active.is_(True),
            )
        )
        return list(dels_for_retry.all())
