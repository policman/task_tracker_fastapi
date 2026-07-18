from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.batch_service import BatchService


@pytest.mark.asyncio
class TestBatchServiceUnit:

    async def test_get_batch_statistics_math(self):
        mock_session = AsyncMock()

        service = BatchService(session=mock_session)

        mock_batch = MagicMock()
        mock_batch.id = 1
        mock_batch.batch_number = 1001
        mock_batch.is_closed = False
        mock_batch.created_at = datetime.now(UTC) - timedelta(hours=2)
        mock_batch.work_center_id = 1

        service.get_batch = AsyncMock(return_value=mock_batch)

        service.batch_repo.get_batch_product_counts = AsyncMock(
            return_value={"total": 1000, "aggregated": 500}
        )

        stats = await service.get_batch_statistics(batch_id=1)

        assert stats["production_stats"]["aggregation_rate"] == 50.0
        assert stats["production_stats"]["remaining"] == 500

        assert stats["timeline"]["products_per_hour"] == 250.0

        assert stats["team_performance"]["efficiency_score"] == 100.0
