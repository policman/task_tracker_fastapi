import asyncio
import os

from pydantic import ValidationError

from app.api.v1.schemas.batch import BatchCreate
from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import DatabaseHelper
from app.data.repositories.batch_repository import BatchRepository
from app.storage.minio_service import storage_service
from app.utils.csv_parser import parse_csv_generator
from app.utils.excel_parser import parse_excel_generator
from app.domain.services.webhook_service import WebhookService


@celery_app.task(bind=True, max_retries=1)
def import_batches_from_file(self, object_name: str, user_id: int | None = None):
    ext = object_name.split(".")[-1]
    temp_file_path = f"/tmp/{object_name}"

    async def _logic():
        db_local = DatabaseHelper(database_url=settings.database_url, echo=False)
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

            async with db_local.session_factory() as session:
                webhook_service = WebhookService(session)
                batch_repo = BatchRepository(session)

                batches_for_webhook = []

                for row_idx, row_data in row_generator:
                    try:
                        batch_schema = BatchCreate.model_validate(row_data)

                        if await batch_repo.exists_by_number_date(
                            batch_schema.batch_number,
                            batch_schema.batch_date,
                        ):
                            skipped += 1
                            errors.append(
                                {
                                    "row": row_idx,
                                    "error": f"Batch №{batch_schema.batch_number} "
                                    f"by {batch_schema.batch_date}",
                                }
                            )
                            continue

                        new_batch = await batch_repo.create_batch(batch_schema.model_dump())
                        batches_for_webhook.append(new_batch)
                        created += 1

                        if created % 100 == 0:
                            await webhook_service.trigger_batches_created_bulk(batches_for_webhook)
                            await session.commit()
                            batches_for_webhook.clear()

                    except ValidationError as e:
                        skipped += 1
                        error_detail = e.errors()[0]
                        field_name = (
                            error_detail["loc"][0] if error_detail.get("loc") else "Unknown"
                        )
                        error_msg = error_detail["msg"]

                        errors.append({"row": row_idx, "error": f"Field {field_name}: {error_msg}"})

                    except Exception as e:
                        await session.rollback()
                        skipped += 1
                        errors.append({"row": row_idx, "error": f"Saving error: {str(e)}"})
                        batches_for_webhook.clear()

                if batches_for_webhook:
                    await webhook_service.trigger_batches_created_bulk(batches_for_webhook)

                await webhook_service.trigger_import_completed(
                    total_rows=created + skipped,
                    created=created,
                    skipped=skipped,
                    errors=errors,
                )

                try:
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    errors.append({"row": "final_commit", "error": str(e)})

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
            await db_local.dispose()

    try:
        return asyncio.run(_logic())
    except Exception as e:
        raise self.retry(exc=e)