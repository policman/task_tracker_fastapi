import asyncio
import os

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import db_helper
from app.data.repositories.batch_repository import BatchRepository
from app.storage.minio_service import storage_service
from app.utils.csv_generator import generate_batches_csv
from app.utils.excel_generator import generate_batches_excel


@celery_app.task(bind=True, max_retries=3)
def export_batches_to_file(self, filters: dict, format_file: str = "excel"):

    async def _logic():
        file_path = None
        try:
            async with db_helper.session_factory() as session:
                batch_repo = BatchRepository(session)
                batches_for_export = await batch_repo.get_batches_for_export(filters)

                if format_file == "excel":
                    file_path = generate_batches_excel(batches_for_export)
                else:
                    file_path = generate_batches_csv(batches_for_export)

                presigned_url = storage_service.upload_file(
                    bucket=settings.minio.bucket_exports,
                    object_name=file_path.split("/")[-1],
                    file_path=file_path,
                )

                return {
                    "success": True,
                    "file_url": presigned_url,
                    "total_batches": len(batches_for_export),
                }

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            await db_helper.dispose()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        raise self.retry(exc=e, countdown=10)
