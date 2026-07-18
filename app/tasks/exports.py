import asyncio
import logging

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import DatabaseHelper
from app.domain.services.export_service import BatchExportService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    name="export_batches_to_file_task",
)
def export_batches_to_file(self, filters: dict, format_file: str = "excel"):
    async def _logic():
        db_local = DatabaseHelper(database_url=settings.database_url, echo=False)
        try:
            async with db_local.session_factory() as session:
                export_service = BatchExportService(session)
                return await export_service.export_batches(filters, format_file)
        finally:
            await db_local.dispose()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        logger.warning(f"Error with export batches. Starting retry. Error: {e}")
        raise self.retry(exc=e, countdown=10)
