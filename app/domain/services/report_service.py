import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.services.analytics_service import stats_report_data
from app.domain.services.batch_service import BatchService
from app.domain.services.product_service import ProductService
from app.domain.services.webhook_service import WebhookService
from app.storage.minio_service import storage_service
from app.utils.excel_generator import generate_batch_excel_report
from app.utils.pdf_generator import generate_batch_pdf_report

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.batch_service = BatchService(session)
        self.product_service = ProductService(session)
        self.webhook_service = WebhookService(session)

    async def generate_batch_report(
        self, batch_id: int, report_format: str, user_email: str = None
    ) -> dict:
        file_path = None
        try:
            logger.info(
                f"Начало генерации отчета {report_format} для партии {batch_id}"
            )

            batch_data = await self.batch_service.batch_report_data(batch_id)
            products_data = await self.product_service.products_report_data(batch_id)
            stats_data = await stats_report_data(batch_data, products_data)

            match report_format:
                case "excel":
                    file_path = generate_batch_excel_report(
                        batch_data, products_data, stats_data
                    )
                    ext = "xlsx"
                case "pdf":
                    file_path = generate_batch_pdf_report(
                        batch_data, products_data, stats_data
                    )
                    ext = "pdf"
                case _:
                    raise ValueError(f"Unsupported format: {report_format}")

            object_name = f"batch_{batch_id}_report_{uuid.uuid4().hex}.{ext}"
            file_size = os.path.getsize(file_path)
            expires_at = datetime.now(UTC) + timedelta(hours=1)

            file_url = storage_service.upload_file(
                bucket=settings.minio.bucket_reports,
                object_name=object_name,
                file_path=file_path,
            )

            await self.webhook_service.trigger_report_generated(
                batch_id=batch_id, report_type=report_format, file_url=file_url
            )
            await self.session.commit()

            return {
                "success": True,
                "file_url": file_url,
                "file_name": object_name,
                "file_size": file_size,
                "expires_at": expires_at,
            }

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Локальный файл отчета {file_path} удален.")
