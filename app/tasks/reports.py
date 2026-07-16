import asyncio
import logging

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import DatabaseHelper
from app.domain.services.report_service import ReportService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="generate_batch_report")
def generate_batch_report(
    self,
    batch_id: int,
    report_format: str = "excel",
    user_email: str = None,
):
    async def _logic():
        db_local = DatabaseHelper(database_url=settings.database_url, echo=False)
        try:
            async with db_local.session_factory() as session:
                report_service = ReportService(session)
                return await report_service.generate_batch_report(
                    batch_id, report_format, user_email
                )
        finally:
            await db_local.dispose()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        logger.warning(
            f"Ошибка генерации отчета для партии {batch_id}, запуск retry. Ошибка: {e}"
        )
        raise self.retry(exc=e, countdown=5)
