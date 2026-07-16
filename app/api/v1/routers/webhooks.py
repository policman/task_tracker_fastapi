from fastapi import APIRouter, Depends, status

from app.api.v1.schemas.webhook import (
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
)
from app.core.dependencies import get_webhook_service
from app.domain.services.webhook_service import WebhookService

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


@router.post(
    "/", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    sub_in: WebhookSubscriptionCreate,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    return await webhook_service.create_subscription(sub_in.model_dump())


@router.get("/", response_model=list[WebhookSubscriptionResponse])
async def get_subscriptions(
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    return await webhook_service.get_subscriptions()


@router.patch("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def update_subscription(
    webhook_id: int,
    sub_update: WebhookSubscriptionUpdate,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    update_data = sub_update.model_dump(exclude_unset=True)
    return await webhook_service.update_subscription(webhook_id, update_data)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    webhook_id: int, webhook_service: WebhookService = Depends(get_webhook_service)
):
    await webhook_service.delete_subscription(webhook_id)


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: int,
    limit: int = 20,
    offset: int = 0,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    return await webhook_service.get_webhook_deliveries(webhook_id, limit, offset)
