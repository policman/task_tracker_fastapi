from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.task import BatchGenerateData
from app.data.repositories.batch_repository import BatchRepository


async def batch_report_data(session: AsyncSession, batch_id: int) -> BatchGenerateData:
    repo = BatchRepository(session)
    batch = await repo.get_batch(batch_id)

    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

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
