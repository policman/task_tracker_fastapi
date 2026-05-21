import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.celery_app import celery_app
from app.domain.services.batch_service import batch_report_data
from app.domain.services.product_service import products_report_data
from app.domain.services.analytics_service import stats_report_data
from app.core.database import db_helper
from app.utils.excel_generator import generate_batch_excel_report
from app.storage.minio_service import storage_service
from app.utils.pdf_generator import generate_batch_pdf_report

@celery_app.task(bind=True, max_retries=3, name='generate_batch_report')
def generate_batch_report(
        self,
        batch_id: int,
        report_format: str = "excel",
        user_email: str = None,
):
    async def _logic():
        try:
            async with db_helper.session_factory() as session:
                batch_data = await batch_report_data(session, batch_id)
                products_data = await products_report_data(session, batch_id)
                stats_data = await stats_report_data(batch_data, products_data)

            match report_format:
                case "excel":
                    file_path = generate_batch_excel_report(batch_data, products_data, stats_data)
                    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ext = "xlsx"
                case "pdf":
                    file_path = generate_batch_pdf_report(batch_data, products_data, stats_data)
                    content_type = "application/pdf"
                    ext = "pdf"
                case _:
                    raise ValueError(f"Unsupported format: {report_format}")


            object_name = f"batch_{batch_id}_report_{uuid.uuid4().hex}.{ext}"
            file_size = os.path.getsize(file_path)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            try:
                file_url = storage_service.upload_file(
                    bucket=settings.minio.bucket_reports,
                    object_name=object_name,
                    file_path=file_path,
                    content_type=content_type,
                )

            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

            return {
                "success": True,
                "file_url": file_url,
                "file_name": object_name,
                "file_size": file_size,
                "expires_at": expires_at,
            }
        finally:
            await db_helper.dispose()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        raise self.retry(exc=e, max_retries=3)
