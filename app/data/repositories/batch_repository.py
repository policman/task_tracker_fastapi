from datetime import UTC, date, datetime

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

    async def get_batch_statistics(self, batch_id: int) -> dict:
        result = (
            await self.session.execute(
                select(
                    func.count(Product.id).label("total"),
                    func.sum(case((Product.is_aggregated.is_(True), 1), else_=0)).label(
                        "aggregated"
                    ),
                ).where(Product.batch_id == batch_id)
            )
        ).first()

        total = result.total or 0
        aggregated = result.aggregated or 0

        return {"total": total, "aggregated": aggregated}

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

        await self.session.commit()
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
        batch_stats = (
            await self.session.execute(
                select(
                    func.count(Batch.id).label("total_batches"),
                    func.sum(case((Batch.is_closed == False, 1), else_=0)).label("active_batches"),
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
                )
            )
        ).one()

        total_products = product_stats.total_products or 0
        aggregated_products = int(product_stats.aggregated_products or 0)

        if total_products > 0:
            aggregation_rate = round((aggregated_products / total_products) * 100, 2)
        else:
            aggregation_rate = 0.0

        return {
            "total_batches": batch_stats.total_batches or 0,
            "active_batches": int(batch_stats.active_batches or 0),
            "total_products": product_stats.total_products or 0,
            "aggregated_products": int(product_stats.aggregated_products or 0),
            "aggregation_rate": aggregation_rate,
            "cached_at": datetime.now(UTC).isoformat(),
        }
