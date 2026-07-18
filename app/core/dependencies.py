from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_helper
from app.domain.services.batch_service import BatchService
from app.domain.services.product_service import ProductService
from app.domain.services.webhook_service import WebhookService


async def get_batch_service(
    session: AsyncSession = Depends(db_helper.session_getter),
) -> BatchService:
    return BatchService(session)


async def get_product_service(
    session: AsyncSession = Depends(db_helper.session_getter),
) -> ProductService:
    return ProductService(session)


async def get_webhook_service(
    session: AsyncSession = Depends(db_helper.session_getter),
) -> WebhookService:
    return WebhookService(session)


async def get_db(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    return session
