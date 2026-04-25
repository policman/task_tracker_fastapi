from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.data.models.batch import Batch
from app.data.models.work_center import WorkCenter


class BatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_batch(self, batch_data: dict) -> Batch:

        work_center = await self.session.scalar(
            select(WorkCenter)
            .where(WorkCenter.identifier == batch_data["work_center_identifier"])
        )

        if not work_center:
            work_center = WorkCenter(
                identifier=batch_data["work_center_identifier"],
                name=batch_data["work_center_identifier"]
            )
            self.session.add(work_center)
            await self.session.flush()

        batch_dict = {k: v for k, v in batch_data.items() if k not in (
            "work_center_identifier", "work_center_name"
        )}

        new_batch = Batch(**batch_dict, work_center_id=work_center.id)
        self.session.add(new_batch)

        await self.session.commit()
        # await self.session.refresh(new_batch)

        return await self.get_batch(new_batch.id)

    async def get_batch(self, batch_id: int) -> Batch | None:
        return await self.session.scalar(
            select(Batch)
            .where(Batch.id == batch_id)
            .options(selectinload(Batch.products))
        )


    async def get_filtered_batch(self, filters: dict):
        limit = filters.pop("limit", 20)
        offset = filters.pop("offset", 0)

        result = await self.session.scalars(
            select(Batch)
            .filter_by(**filters)
            .options(selectinload(Batch.products))
            .offset(offset)
            .limit(limit)
        )

        return list(result.all())


    async def update_batch(self, batch_id: int, update_data: dict) -> Batch | None:
        batch = await self.get_batch(batch_id)

        if not batch:
            return None

        if "is_closed" in update_data:
            new_status = update_data["is_closed"]
            batch.is_closed = new_status

            if new_status is True:
                batch.closed_at = datetime.now(timezone.utc)
            else:
                batch.closed_at = None

        await self.session.commit()
        await self.session.refresh(batch)

        return batch



