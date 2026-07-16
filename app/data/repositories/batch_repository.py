from datetime import UTC, date, datetime

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.models.batch import Batch
from app.data.models.product import Product
from app.data.models.work_center import WorkCenter
from app.data.repositories.base_repository import BaseRepository


class BatchRepository(BaseRepository[Batch]):
    def __init__(self, session: AsyncSession):
        self.session = session
        super().__init__(model=Batch, session=session)

    async def create_or_get_work_center(self, identifier: str, name: str) -> WorkCenter:
        work_center = await self.session.scalar(
            select(WorkCenter).where(WorkCenter.identifier == identifier)
        )

        if not work_center:
            work_center = WorkCenter(
                identifier=identifier,
                name=name,
            )
            self.session.add(work_center)
            await self.session.flush()

        return work_center

    async def get_batch_product_counts(self, batch_id: int) -> dict:

        result = (
            await self.session.execute(
                select(
                    func.count(Product.id).label("total"),
                    func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label(
                        "aggregated"
                    ),
                ).where(Product.batch_id == batch_id)
            )
        ).one()

        return {
            "total": result.total or 0,
            "aggregated": result.aggregated or 0,
        }

    async def get_batch_with_products(self, batch_id: int) -> Batch | None:
        return await self.session.scalar(
            select(Batch)
            .where(Batch.id == batch_id)
            .options(selectinload(Batch.products))
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

    async def exists_by_number_date(self, batch_number: int, batch_date: date) -> bool:
        result = await self.session.scalar(
            select(Batch).where(
                Batch.batch_number == batch_number, Batch.batch_date == batch_date
            )
        )
        return result is not None

    async def get_batches_for_export(self, filters: dict) -> list[Batch]:
        query = select(Batch)
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

    async def get_raw_dashboard_statistics(self) -> dict:
        now = datetime.now(UTC)
        today = now.date()

        batch_stats = (
            await self.session.execute(
                select(
                    func.count(Batch.id).label("total_batches"),
                    func.sum(case((Batch.is_closed.is_(False), 1), else_=0)).label(
                        "active_batches"
                    ),
                    func.sum(case((Batch.is_closed.is_(True), 1), else_=0)).label(
                        "closed_batches"
                    ),
                    func.sum(
                        case((func.date(Batch.created_at) == today, 1), else_=0)
                    ).label("today_created"),
                    func.sum(
                        case((func.date(Batch.closed_at) == today, 1), else_=0)
                    ).label("today_closed"),
                )
            )
        ).one()

        product_stats = (
            await self.session.execute(
                select(
                    func.count(Product.id).label("total_products"),
                    func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label(
                        "aggregated_products"
                    ),
                    func.sum(
                        case((func.date(Product.created_at) == today, 1), else_=0)
                    ).label("today_added"),
                    func.sum(
                        case((func.date(Product.aggregated_at) == today, 1), else_=0)
                    ).label("today_aggregated"),
                )
            )
        ).one()

        hour_expr = func.extract("hour", Batch.created_at)
        shift_expr = case(
            ((hour_expr >= 8) & (hour_expr < 16), "1 смена"),
            ((hour_expr >= 16) & (hour_expr <= 23), "2 смена"),
            else_="3 смена",
        )

        shift_stmt = (
            select(
                shift_expr.label("shift_name"),
                func.count(Batch.id.distinct()).label("batches"),
                func.count(Product.id).label("products"),
                func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label(
                    "aggregated"
                ),
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .group_by(shift_expr)
        )
        shift_results = (await self.session.execute(shift_stmt)).all()

        wc_stmt = (
            select(
                Batch.work_center_id,
                func.count(Batch.id.distinct()).label("batches_count"),
                func.count(Product.id).label("products_count"),
                func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label(
                    "aggregated"
                ),
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .group_by(Batch.work_center_id)
            .order_by(func.count(Product.id).desc())
            .limit(5)
        )
        wc_results = (await self.session.execute(wc_stmt)).all()

        return {
            "batch_stats": batch_stats,
            "product_stats": product_stats,
            "shift_results": shift_results,
            "wc_results": wc_results,
            "now": now,
        }

    async def get_batches_for_comparison(self, batch_ids: list[int]) -> list[dict]:
        results = await self.session.execute(
            select(
                Batch.id,
                Batch.batch_number,
                Batch.created_at,
                Batch.closed_at,
                Batch.is_closed,
                func.count(Product.id).label("total_products"),
                func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label(
                    "aggregated"
                ),
            )
            .outerjoin(Product, Product.batch_id == Batch.id)
            .where(Batch.id.in_(batch_ids))
            .group_by(Batch.id)
        )
        return results.all()
