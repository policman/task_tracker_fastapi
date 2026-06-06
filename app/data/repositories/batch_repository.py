from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.models.batch import Batch
from app.data.models.product import Product
from app.data.models.work_center import WorkCenter


class BatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_batch(self, batch_data: dict) -> Batch:

        work_center = await self.session.scalar(
            select(WorkCenter).where(WorkCenter.identifier == batch_data["work_center_identifier"])
        )

        if not work_center:
            work_center = WorkCenter(
                identifier=batch_data["work_center_identifier"],
                name=batch_data["work_center_identifier"],
            )
            self.session.add(work_center)
            await self.session.flush()

        batch_dict = {
            k: v
            for k, v in batch_data.items()
            if k not in ("work_center_identifier", "work_center_name")
        }

        new_batch = Batch(**batch_dict, work_center_id=work_center.id)
        self.session.add(new_batch)

        await self.session.commit()
        await self.session.flush()

        return new_batch

    async def get_batch(self, batch_id: int) -> Batch | None:
        return await self.session.scalar(select(Batch).where(Batch.id == batch_id))

    async def get_batch_statistics(self, batch_id: int) -> dict | None:
        batch = await self.session.get(Batch, batch_id)
        if not batch:
            return None

        result = (
            await self.session.execute(
                select(
                    func.count(Product.id).label("total"),
                    func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label("aggregated"),
                ).where(Product.batch_id == batch_id)
            )
        ).one()

        total = result.total or 0
        aggregated = int(result.aggregated or 0)
        remaining = total - aggregated
        rate = round((aggregated / total * 100), 2) if total > 0 else 0.0

        now = datetime.now(UTC)
        created_at = batch.created_at if batch.created_at.tzinfo else batch.created_at.replace(tzinfo=UTC)

        if batch.is_closed and batch.closed_at:
            closed_at = batch.closed_at if batch.closed_at.tzinfo else batch.closed_at.replace(tzinfo=UTC)
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
        efficiency_score = round((products_per_hour / target_products_per_hour) * 100,
                                 2) if target_products_per_hour > 0 else 0.0

        team_name = f"Рабочий центр {batch.work_center_id}" if getattr(batch, 'work_center_id',
                                                                       None) else "Основная бригада"

        return {
            "batch_info": {
                "id": batch.id,
                "batch_number": batch.batch_number,
                "batch_date": batch.batch_date,
                "is_closed": batch.is_closed
            },
            "production_stats": {
                "total_products": total,
                "aggregated": aggregated,
                "remaining": remaining,
                "aggregation_rate": rate
            },
            "timeline": {
                "shift_duration_hours": shift_duration_hours,
                "elapsed_hours": round(elapsed_hours, 2),
                "products_per_hour": products_per_hour,
                "estimated_completion": estimated_completion
            },
            "team_performance": {
                "team": team_name,
                "avg_products_per_hour": products_per_hour,
                "efficiency_score": min(efficiency_score, 100.0)
            }
        }

    async def get_batch_with_products(self, batch_id: int) -> Batch | None:
        return await self.session.scalar(
            select(Batch).where(Batch.id == batch_id).options(selectinload(Batch.products))
        )

    async def get_filtered_batch(self, filters: dict) -> list[Batch]:
        limit = filters.pop("limit", 20)
        offset = filters.pop("offset", 0)

        return list(
            (
                await self.session.scalars(
                    select(Batch).filter_by(**filters).offset(offset).limit(limit)
                )
            ).all()
        )

    async def update_batch(self, batch_id: int, update_data: dict) -> Batch | None:
        batch = await self.get_batch(batch_id)

        if not batch:
            return None

        if "is_closed" in update_data:
            new_status = update_data["is_closed"]
            batch.is_closed = new_status

            if new_status is True:
                batch.closed_at = datetime.now(UTC)
            else:
                batch.closed_at = None

        await self.session.flush()
        await self.session.refresh(batch)

        return batch

    async def exists_by_number_date(self, batch_number: int, batch_date: date) -> bool:
        result = await self.session.scalar(
            select(Batch).where(Batch.batch_number == batch_number, Batch.batch_date == batch_date)
        )

        return result is not None

    async def get_batches_for_export(self, filters: dict) -> list[Batch]:
        query = select(Batch)

        # Список условий для and_
        conditions = []

        if filters.get("is_closed") is not None:
            conditions.append(Batch.is_closed == filters["is_closed"])

        if filters.get("date_from"):
            conditions.append(Batch.batch_date >= filters["date_from"])

        if filters.get("date_to"):
            conditions.append(Batch.batch_date <= filters["date_to"])

        if filters.get("batch_number"):
            conditions.append(Batch.batch_number == filters["batch_number"])

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Batch.batch_date.desc())

        result = await self.session.scalars(query)
        return list(result.all())

    async def auto_close_expired_batches(self) -> int:

        now = datetime.now(UTC)

        result = await self.session.execute(
            update(Batch)
            .where(Batch.is_closed == False)
            .where(Batch.shift_end < now)
            .values(is_closed=True)
        )

        return result.rowcount

    async def update_cached_statistics(self) -> dict:
        now = datetime.now(UTC)
        today = now.date()

        batch_stats = (
            await self.session.execute(
                select(
                    func.count(Batch.id).label("total_batches"),
                    func.sum(case((Batch.is_closed.is_(False), 1), else_=0)).label("active_batches"),
                    func.sum(case((Batch.is_closed.is_(True), 1), else_=0)).label("closed_batches"),
                    func.sum(case((func.date(Batch.created_at) == today, 1), else_=0)).label("today_created"),
                    func.sum(case((func.date(Batch.closed_at) == today, 1), else_=0)).label("today_closed"),
                )
            )
        ).one()

        product_stats = (
            await self.session.execute(
                select(
                    func.count(Product.id).label("total_products"),
                    func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label("aggregated_products"),
                    func.sum(case((func.date(Product.created_at) == today, 1), else_=0)).label("today_added"),
                    func.sum(case((func.date(Product.aggregated_at) == today, 1), else_=0)).label("today_aggregated"),
                )
            )
        ).one()

        hour_expr = func.extract('hour', Batch.created_at)
        shift_expr = case(
            ((hour_expr >= 8) & (hour_expr < 16), "1 смена"),
            ((hour_expr >= 16) & (hour_expr <= 23), "2 смена"),
            else_="3 смена"
        )

        shift_stmt = (
            select(
                shift_expr.label("shift_name"),
                func.count(Batch.id.distinct()).label("batches"),
                func.count(Product.id).label("products"),
                func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label("aggregated")
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .group_by(shift_expr)
        )
        shift_results = (await self.session.execute(shift_stmt)).all()

        by_shift = {}
        for row in shift_results:
            by_shift[row.shift_name] = {
                "batches": row.batches or 0,
                "products": row.products or 0,
                "aggregated": int(row.aggregated or 0)
            }

        for s in ["1 смена", "2 смена", "3 смена"]:
            if s not in by_shift:
                by_shift[s] = {"batches": 0, "products": 0, "aggregated": 0}

        wc_stmt = (
            select(
                Batch.work_center_id,
                func.count(Batch.id.distinct()).label("batches_count"),
                func.count(Product.id).label("products_count"),
                func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label("aggregated")
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .group_by(Batch.work_center_id)
            .order_by(func.count(Product.id).desc())
            .limit(5)
        )
        wc_results = (await self.session.execute(wc_stmt)).all()

        top_work_centers = []
        for row in wc_results:
            t_prod = row.products_count or 0
            a_prod = row.aggregated or 0
            rate = round((a_prod / t_prod * 100), 2) if t_prod > 0 else 0.0

            wc_id_str = str(row.work_center_id) if row.work_center_id else "unknown"
            wc_name = f"Рабочий центр {row.work_center_id}" if row.work_center_id else "Неизвестный цех"

            top_work_centers.append({
                "id": wc_id_str,
                "name": wc_name,
                "batches_count": row.batches_count or 0,
                "products_count": t_prod,
                "aggregation_rate": rate
            })

        total_products = product_stats.total_products or 0
        aggregated_products = int(product_stats.aggregated_products or 0)
        aggregation_rate = round((aggregated_products / total_products) * 100, 2) if total_products > 0 else 0.0

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

    async def compare_batches(self, batch_ids: list[int]) -> list[dict]:
        now = datetime.now(UTC)

        stmt = (
            select(
                Batch.id,
                Batch.batch_number,
                Batch.created_at,
                Batch.closed_at,
                Batch.is_closed,
                func.count(Product.id).label("total_products"),
                func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label("aggregated")
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .where(Batch.id.in_(batch_ids))
            .group_by(Batch.id)
        )

        results = (await self.session.execute(stmt)).all()

        comparison = []

        for row in results:
            total = row.total_products or 0
            agg = int(row.aggregated or 0)
            rate = round((agg / total * 100), 2) if total > 0 else 0.0

            created_at = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=UTC)

            if row.is_closed and row.closed_at:
                closed_at = row.closed_at if row.closed_at.tzinfo else row.closed_at.replace(tzinfo=UTC)
                elapsed_seconds = (closed_at - created_at).total_seconds()
            else:
                elapsed_seconds = (now - created_at).total_seconds()

            elapsed_hours = max(elapsed_seconds / 3600, 0.01)
            products_per_hour = round(agg / elapsed_hours, 2)

            comparison.append({
                "batch_id": row.id,
                "batch_number": row.batch_number,
                "total_products": total,
                "aggregated": agg,
                "rate": rate,
                "duration_hours": round(elapsed_hours, 2),
                "products_per_hour": products_per_hour
            })

        return comparison