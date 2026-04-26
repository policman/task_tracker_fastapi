import asyncio, tempfile, openpyxl, os
from datetime import datetime

from app.storage.minio_service import storage_service
from app.core.config import settings
from app.celery_app import celery_app
from app.core.database import db_helper
from app.data.repositories.product_repository import ProductRepository


@celery_app.task(bind=True, name="aggregate_products_batch")
def aggregate_products_batch(self, batch_id: int, unique_codes: list[str]):

    async def _aggregate_logic():
        async with db_helper.session_factory() as session:
            repo = ProductRepository(session)
            updated_count = await repo.aggregate_products(batch_id, unique_codes)

            total_requested = len(unique_codes)
            return {
                "success": True,
                "total": total_requested,
                "aggregated": updated_count,
                "failed": total_requested - updated_count,
            }

    return asyncio.run(_aggregate_logic())


@celery_app.task(bind=True, name="generate_batch_report")
def generate_batch_report(self, batch_id: int):

    async def _generate_logic():
        async with db_helper.session_factory() as session:
            product_repo = ProductRepository(session)
            products = await product_repo.get_batch_products(batch_id)

            wb = openpyxl.Workbook()

            #list 1
            ws_info = wb.active
            ws_info.title = "Информация о партии"
            ws_info.append(["Номер партии", f"Партия №{batch_id}"])
            ws_info.append(["Дата генерации", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            ws_info.append(["Всего продукции", len(products)])

            #list 2
            ws_products = wb.create_sheet("Продукция")
            ws_products.append(["ID", "Уникальный код", "Аггрегирована", "Дата аггрегации"])

            aggregated_count = 0
            for p in products:
                status = "Да" if p.is_aggregated else "Нет"
                date_agg = p.aggregated_at.strftime("%Y-%m-%d %H:%M:%S") if p.aggregated_at else "-"
                ws_products.append([p.id, p.unique_code, status, date_agg])

                if p.is_aggregated:
                    aggregated_count += 1

            #list 3
            ws_stats = wb.create_sheet("Статистика")
            ws_stats.append(["Всего", len(products)])
            ws_stats.append(["Аггрегировано", aggregated_count])
            rate = (aggregated_count / len(products) * 100) if products else 0
            ws_stats.append(["Процент выполнения", f"{rate:.1f}%"])

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                temp_file_path = tmp.name
                wb.save(temp_file_path)

            try:
                file_name = f"batch_{batch_id}_report_{int(datetime.now().timestamp())}.xlsx"

                url = storage_service.upload_file(
                    bucket=settings.minio.bucket_reports,
                    object_name=file_name,
                    file_path=temp_file_path,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                return {
                    "success": True,
                    "file_url": url,
                    "file_name": file_name
                }
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

    return asyncio.run(_generate_logic())