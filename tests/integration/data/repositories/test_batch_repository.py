from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import Batch, WorkCenter
from app.data.repositories.batch_repository import BatchRepository


@pytest.mark.asyncio
class TestBatchRepository:

    async def test_get_raw_dashboard_statistics(self, db_session: AsyncSession):
        repo = BatchRepository(db_session)

        wc = WorkCenter(identifier="123", name="Цех №1")
        db_session.add(wc)
        await db_session.flush()

        now = datetime.now(UTC)

        fake_shift_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
        fake_shift_end = now.replace(hour=20, minute=0, second=0, microsecond=0)

        batch1 = Batch(
            batch_number=1001,
            task_description="test1",
            batch_date=now.date(),
            work_center_id=wc.id,
            is_closed=False,
            shift="1",
            team="Бригада А",
            nomenclature="Продукт А",
            ekn_code="test_ekn1",
            shift_start=fake_shift_start,
            shift_end=fake_shift_end,
        )
        batch2 = Batch(
            batch_number=1002,
            task_description="test2",
            batch_date=now.date(),
            work_center_id=wc.id,
            is_closed=False,
            shift="2",
            team="Бригада Б",
            nomenclature="Продукт Б",
            ekn_code="test_ekn2",
            shift_start=fake_shift_start,
            shift_end=fake_shift_end,
        )
        batch3 = Batch(
            batch_number=1003,
            task_description="test3",
            batch_date=now.date() - timedelta(days=1),
            work_center_id=wc.id,
            is_closed=True,
            closed_at=now,
            shift="1",
            team="Бригада А",
            nomenclature="Продукт В",
            ekn_code="test_ekn3",
            shift_start=fake_shift_start - timedelta(days=1),
            shift_end=fake_shift_end - timedelta(days=1),
        )

        db_session.add_all([batch1, batch2, batch3])
        await db_session.commit()

        result = await repo.get_raw_dashboard_statistics()

        batch_stats = result["batch_stats"]

        assert batch_stats.total_batches == 3
        assert batch_stats.active_batches == 2
        assert batch_stats.closed_batches == 1
