from datetime import UTC, datetime, timedelta
from logging import getLogger

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.task import BatchGenerateData
from app.core.cache import redis_service
from app.core.exceptions import DuplicationException, NotFoundException
from app.data.models import Batch
from app.data.repositories.batch_repository import BatchRepository
from app.domain.services.webhook_service import WebhookService

logger = getLogger(__name__)


class BatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.batch_repo = BatchRepository(session)
        self.webhook_service = WebhookService(session)

    async def get_batch(self, batch_id: int) -> Batch:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise NotFoundException(message=f"Batch with ID {batch_id} not found")

        return batch

    async def bulk_create_batches(self, batches_data: list[dict]):
        count_batches = len(batches_data)
        logger.info(f"Start bulk creation of {count_batches} batches")
        created_batches = []

        work_center_cache: dict[str, int] = {}

        try:
            for batch_data in batches_data:
                wc_identifier = batch_data.pop("work_center_identifier")
                wc_name = batch_data.pop("work_center_name", wc_identifier)

                if wc_identifier not in work_center_cache:
                    work_center = await self.batch_repo.create_or_get_work_center(
                        identifier=wc_identifier, name=wc_name
                    )
                    work_center_cache[wc_identifier] = work_center.id

                batch_data["work_center_id"] = work_center_cache[wc_identifier]

                new_batch = await self.batch_repo.create(batch_data)
                created_batches.append(new_batch)

            await self.session.commit()
            logger.info(f"Finished bulk creation of {count_batches} batches")

            await self.webhook_service.trigger_batches_created_bulk(created_batches)
            logger.info("Webhook of bulk creation sent")

            await redis_service.delete("dashboard_stats")
            await redis_service.delete_pattern("batches_filtered_list:*")
            logger.debug("Cache dashboard and batches_list are deleted")

            return created_batches

        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(
                f"Error with creation of {count_batches} batches. May be duplicate numbers"
                f"Details: {str(e)}"
            )
            raise DuplicationException("One or more batches already exist.")

        except Exception:
            await self.session.rollback()
            logger.exception(f"Critical error with creation of {count_batches} batches")
            raise

    async def batch_report_data(self, batch_id: int) -> BatchGenerateData:
        batch = await self.get_batch(batch_id)

        logger.info(f"Got batch {batch_id} for reporting data")

        return BatchGenerateData(
            batch_number=batch.batch_number,
            batch_date=batch.batch_date,
            is_closed=batch.is_closed,
            work_center_id=batch.work_center_id,
            shift=batch.shift,
            team=batch.team,
            nomenclature=batch.nomenclature,
            shift_start=batch.shift_start,
            shift_end=batch.shift_end,
        )

    async def get_batch_with_products(self, batch_id: int) -> Batch:
        batch = await self.batch_repo.get_batch_with_products(batch_id)

        if not batch:
            logger.warning(f"Not found batch {batch_id}")
            raise NotFoundException(f"Batch {batch_id} not found")

        return batch

    async def get_filtered_batch(self, filters: dict) -> list[Batch]:
        return await self.batch_repo.get_filtered_batch(filters)

    async def get_batch_statistics(self, batch_id: int) -> dict:
        batch = await self.get_batch(batch_id)

        counts = await self.batch_repo.get_batch_product_counts(batch_id)

        total = counts["total"]
        aggregated = counts["aggregated"]

        remaining = total - aggregated
        rate = round((aggregated / total * 100), 2) if total > 0 else 0.0

        now = datetime.now(UTC)
        created_at = (
            batch.created_at
            if batch.created_at.tzinfo
            else batch.created_at.replace(tzinfo=UTC)
        )

        if batch.is_closed and batch.closed_at:
            closed_at = (
                batch.closed_at
                if batch.closed_at.tzinfo
                else batch.closed_at.replace(tzinfo=UTC)
            )
            elapsed_seconds = (closed_at - created_at).total_seconds()
        else:
            elapsed_seconds = (now - created_at).total_seconds()

        elapsed_hours = max(elapsed_seconds / 3600, 0.01)
        products_per_hour = round(aggregated / elapsed_hours, 2)

        estimated_completion = None
        if not batch.is_closed and products_per_hour > 0 and remaining > 0:
            hours_left = remaining / products_per_hour
            estimated_completion = now + timedelta(hours=hours_left)

        shift_duration_hours = 12.0
        target_products_per_hour = total / shift_duration_hours if total > 0 else 1.0
        efficiency_score = (
            round((products_per_hour / target_products_per_hour) * 100, 2)
            if target_products_per_hour > 0
            else 0.0
        )

        team_name = (
            f"Рабочий центр {batch.work_center_id}"
            if getattr(batch, "work_center_id", None)
            else "Основная бригада"
        )

        return {
            "batch_info": {
                "id": batch.id,
                "batch_number": batch.batch_number,
                "batch_date": batch.batch_date,
                "is_closed": batch.is_closed,
            },
            "production_stats": {
                "total_products": total,
                "aggregated": aggregated,
                "remaining": remaining,
                "aggregation_rate": rate,
            },
            "timeline": {
                "shift_duration_hours": shift_duration_hours,
                "elapsed_hours": round(elapsed_hours, 2),
                "products_per_hour": products_per_hour,
                "estimated_completion": estimated_completion,
            },
            "team_performance": {
                "team": team_name,
                "avg_products_per_hour": products_per_hour,
                "efficiency_score": min(efficiency_score, 100.0),
            },
        }

    async def update_batch(self, batch_id: int, update_data: dict) -> Batch:
        batch = await self.get_batch(batch_id)

        if not update_data:
            return batch

        if "is_closed" in update_data:
            if update_data["is_closed"] is True:
                update_data["closed_at"] = datetime.now(UTC)
            else:
                update_data["closed_at"] = None

        updated_batch = await self.batch_repo.update(batch, update_data)

        await self.webhook_service.trigger_batch_updated(
            batch_id=updated_batch.id,
            batch_number=updated_batch.batch_number,
            changes=update_data,
        )

        if update_data.get("is_closed") is True:
            stats = await self.get_batch_statistics(batch_id)

            await self.webhook_service.trigger_batch_closed(
                batch_id=updated_batch.id,
                batch_number=updated_batch.batch_number,
                closed_at=updated_batch.closed_at,
                statistics=stats,
            )

        await self.session.commit()

        await redis_service.delete(f"batch_detail:batch_id_{batch_id}")
        await redis_service.delete(f"batch_statistics:batch_id_{batch_id}")
        await redis_service.delete("dashboard_stats")
        await redis_service.delete_pattern("batches_filtered_list:*")

        return updated_batch

    async def get_dashboard_statistics(self) -> dict:
        raw_data = await self.batch_repo.get_raw_dashboard_statistics()

        batch_stats = raw_data["batch_stats"]
        product_stats = raw_data["product_stats"]
        shift_results = raw_data["shift_results"]
        wc_results = raw_data["wc_results"]
        now = raw_data["now"]

        by_shift = {}
        for row in shift_results:
            by_shift[row.shift_name] = {
                "batches": row.batches or 0,
                "products": row.products or 0,
                "aggregated": int(row.aggregated or 0),
            }

        for s in ["1 смена", "2 смена", "3 смена"]:
            if s not in by_shift:
                by_shift[s] = {"batches": 0, "products": 0, "aggregated": 0}

        top_work_centers = []
        for row in wc_results:
            t_prod = row.products_count or 0
            a_prod = row.aggregated or 0
            rate = round((a_prod / t_prod * 100), 2) if t_prod > 0 else 0.0

            wc_id_str = str(row.work_center_id) if row.work_center_id else "unknown"
            wc_name = (
                f"Рабочий центр {row.work_center_id}"
                if row.work_center_id
                else "Неизвестный цех"
            )

            top_work_centers.append(
                {
                    "id": wc_id_str,
                    "name": wc_name,
                    "batches_count": row.batches_count or 0,
                    "products_count": t_prod,
                    "aggregation_rate": rate,
                }
            )

        total_products = product_stats.total_products or 0
        aggregated_products = int(product_stats.aggregated_products or 0)
        aggregation_rate = (
            round((aggregated_products / total_products) * 100, 2)
            if total_products > 0
            else 0.0
        )

        return {
            "summary": {
                "total_batches": batch_stats.total_batches or 0,
                "active_batches": int(batch_stats.active_batches or 0),
                "closed_batches": int(batch_stats.closed_batches or 0),
                "total_products": total_products,
                "aggregated_products": aggregated_products,
                "aggregation_rate": aggregation_rate,
            },
            "today": {
                "batches_created": int(batch_stats.today_created or 0),
                "batches_closed": int(batch_stats.today_closed or 0),
                "products_added": int(product_stats.today_added or 0),
                "products_aggregated": int(product_stats.today_aggregated or 0),
            },
            "by_shift": by_shift,
            "top_work_centers": top_work_centers,
            "cached_at": now.isoformat(),
        }

    async def compare_batches(self, batch_ids: list[int]) -> dict:
        now = datetime.now(UTC)
        raw_data = await self.batch_repo.get_batches_for_comparison(batch_ids)

        if not raw_data:
            return {
                "comparison": [],
                "average": {"aggregation_rate": 0.0, "products_per_hour": 0.0},
            }

        comparison = []
        for row in raw_data:
            total = row.total_products or 0
            agg = int(row.aggregated or 0)
            rate = round((agg / total * 100), 2) if total > 0 else 0.0

            created_at = (
                row.created_at
                if row.created_at.tzinfo
                else row.created_at.replace(tzinfo=UTC)
            )

            if row.is_closed and row.closed_at:
                closed_at = (
                    row.closed_at
                    if row.closed_at.tzinfo
                    else row.closed_at.replace(tzinfo=UTC)
                )
                elapsed_seconds = (closed_at - created_at).total_seconds()
            else:
                elapsed_seconds = (now - created_at).total_seconds()

            elapsed_hours = max(elapsed_seconds / 3600, 0.01)
            products_per_hour = round(agg / elapsed_hours, 2)

            comparison.append(
                {
                    "batch_id": row.id,
                    "batch_number": row.batch_number,
                    "total_products": total,
                    "aggregated": agg,
                    "rate": rate,
                    "duration_hours": round(elapsed_hours, 2),
                    "products_per_hour": products_per_hour,
                }
            )

        avg_rate = sum(b["rate"] for b in comparison) / len(comparison)
        avg_speed = sum(b["products_per_hour"] for b in comparison) / len(comparison)

        if not comparison:
            raise NotFoundException(message="Not found batches to compare")

        return {
            "comparison": comparison,
            "average": {
                "aggregation_rate": round(avg_rate, 2),
                "products_per_hour": round(avg_speed, 2),
            },
        }

    async def auto_close_expired_batches(self) -> int:
        count = await self.batch_repo.auto_close_expired_batches()
        await self.session.commit()
        return count
