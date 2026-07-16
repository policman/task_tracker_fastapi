import asyncio
import logging

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import DatabaseHelper
from app.domain.services.import_service import BatchImportService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1)
def import_batches_from_file(self, object_name: str, user_id: int | None = None):
    async def _logic():
        db_local = DatabaseHelper(database_url=settings.database_url, echo=False)
        try:
            async with db_local.session_factory() as session:
                import_service = BatchImportService(session)
                return await import_service.import_batches(object_name)
        finally:
            await db_local.dispose()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        logger.exception(f"Error with import file {object_name}")
        raise self.retry(exc=e, countdown=5)
