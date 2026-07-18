import logging
import os

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.batch import BatchCreate
from app.core.config import settings
from app.data.repositories.batch_repository import BatchRepository
from app.domain.services.webhook_service import WebhookService
from app.storage.minio_service import storage_service
from app.utils.csv_parser import parse_csv_generator
from app.utils.excel_parser import parse_excel_generator

logger = logging.getLogger(__name__)


class BatchImportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.batch_repo = BatchRepository(session)
        self.webhook_service = WebhookService(session)

    async def import_batches(self, object_name: str) -> dict:
        ext = object_name.split(".")[-1]
        temp_file_path = f"/tmp/{object_name}"

        try:
            storage_service.download_file(
                bucket=settings.minio.bucket_imports,
                object_name=object_name,
                file_path=temp_file_path,
            )

            if ext == "xlsx":
                row_generator = parse_excel_generator(temp_file_path)
            elif ext == "csv":
                row_generator = parse_csv_generator(temp_file_path)
            else:
                raise ValueError("Import Error (Supported files: xlsx or csv)")

            created = 0
            skipped = 0
            errors = []
            batches_for_webhook = []

            logger.info(f"Start processing import file: {object_name}")

            for row_idx, row_data in row_generator:
                try:
                    batch_schema = BatchCreate.model_validate(row_data)

                    if await self.batch_repo.exists_by_number_date(
                        batch_schema.batch_number, batch_schema.batch_date
                    ):
                        skipped += 1
                        errors.append(
                            {
                                "row": row_idx,
                                "error": f"Batch №{batch_schema.batch_number} by {batch_schema.batch_date} already exists",
                            }
                        )
                        continue

                    new_batch = await self.batch_repo.create(batch_schema.model_dump())
                    batches_for_webhook.append(new_batch)
                    created += 1

                    if created % 100 == 0:
                        await self.webhook_service.trigger_batches_created_bulk(
                            batches_for_webhook
                        )
                        await self.session.commit()
                        batches_for_webhook.clear()

                except ValidationError as e:
                    skipped += 1
                    error_detail = e.errors()[0]
                    field_name = (
                        error_detail["loc"][0] if error_detail.get("loc") else "Unknown"
                    )
                    errors.append(
                        {
                            "row": row_idx,
                            "error": f"Field {field_name}: {error_detail['msg']}",
                        }
                    )

                except Exception as e:
                    logger.error(f"Error with saving import file {object_name}")
                    await self.session.rollback()
                    skipped += 1
                    errors.append({"row": row_idx, "error": f"Saving error: {str(e)}"})
                    batches_for_webhook.clear()

            if batches_for_webhook:
                await self.webhook_service.trigger_batches_created_bulk(
                    batches_for_webhook
                )

            try:
                await self.session.commit()
            except Exception as e:
                await self.session.rollback()
                errors.append({"row": "final_commit", "error": str(e)})

            await self.webhook_service.trigger_import_completed(
                total_rows=created + skipped,
                created=created,
                skipped=skipped,
                errors=errors,
            )

            logger.info(
                f"File {object_name} successfully imported"
            )

            return {
                "success": True,
                "total_rows": created + skipped,
                "created": created,
                "skipped": skipped,
                "errors": errors,
            }

        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
