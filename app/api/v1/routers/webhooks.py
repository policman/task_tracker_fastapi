from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.webhook import (
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
)
from app.core.database import db_helper
from app.data.repositories.webhook_repository import WebhookRepository

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    sub_in: WebhookSubscriptionCreate,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Creates a new webhook subscription."""
    repo = WebhookRepository(session)
    data = sub_in.model_dump()

    if 'url' in data and data['url']:
        data['url'] = str(data['url'])

    new_subscription = await repo.create_subscription(data)
    await session.commit()

    return new_subscription


@router.get("/", response_model=list[WebhookSubscriptionResponse])
async def get_subscriptions(session: AsyncSession = Depends(db_helper.session_getter)):
    repo = WebhookRepository(session)
    return await repo.get_subscriptions()


@router.patch("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def update_subscription(
    webhook_id: int,
    sub_update: WebhookSubscriptionUpdate,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """On/Off a webhook subscription."""
    repo = WebhookRepository(session)
    update_data = sub_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    updated_sub = await repo.update_subscription(webhook_id, update_data)

    if not updated_sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    await session.commit()
    return updated_sub


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    webhook_id: int,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Deletes a webhook subscription."""
    repo = WebhookRepository(session)
    await repo.delete_subscription(webhook_id)
    await session.commit()


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: int,
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Histories of deliveries for a webhook."""
    repo = WebhookRepository(session)
    deliveries = await repo.get_deliveries(webhook_id, limit, offset)

    return deliveries
