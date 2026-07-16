import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.repositories.batch_repository import BatchRepository
from app.storage.minio_service import storage_service
from app.utils.csv_generator import generate_batches_csv
from app.utils.excel_generator import generate_batches_excel

logger = logging.getLogger(__name__)


class BatchExportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.batch_repo = BatchRepository(session)

    async def export_batches(self, filters: dict, format_file: str) -> dict:
        file_path = None
        try:
            batches_for_export = await self.batch_repo.get_batches_for_export(filters)
            logger.info(f"Найдено {len(batches_for_export)} партий для экспорта.")

            if format_file == "excel":
                file_path = generate_batches_excel(batches_for_export)
            else:
                file_path = generate_batches_csv(batches_for_export)

            object_name = file_path.split("/")[-1]
            presigned_url = storage_service.upload_file(
                bucket=settings.minio.bucket_exports,
                object_name=object_name,
                file_path=file_path,
            )

            logger.info(
                f"Экспорт успешно завершен. Ссылка сгенерирована: {object_name}"
            )

            return {
                "success": True,
                "file_url": presigned_url,
                "total_batches": len(batches_for_export),
            }

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Временный файл {file_path} удален.")
