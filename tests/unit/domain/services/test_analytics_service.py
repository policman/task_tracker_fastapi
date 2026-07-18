from datetime import datetime
from unittest.mock import MagicMock

from app.domain.services.analytics_service import stats_report_data


class TestAnalyticsService:
    async def test_stats_report_data_happy_path(self):
        mock_batch = MagicMock()
        mock_batch.shift_start = datetime(2024, 1, 1, 8, 0, 0)
        mock_batch.shift_end = datetime(2024, 1, 1, 10, 0, 0)

        mock_products = MagicMock()
        mock_products.products = [
            MagicMock(is_aggregated=True),
            MagicMock(is_aggregated=True),
            MagicMock(is_aggregated=True),
            MagicMock(is_aggregated=False),
        ]

        result = await stats_report_data(mock_batch, mock_products)

        assert result.total_products == 4
        assert result.aggregated_products == 3
        assert result.unaggregated_products == 1
        assert result.percent_aggregated == 75.0
        assert result.avg_speed == 1.5

    async def test_stats_report_data_zero_products(self):
        mock_batch = MagicMock()
        mock_batch.shift_start = datetime(2024, 1, 1, 8, 0, 0)
        mock_batch.shift_end = datetime(2024, 1, 1, 10, 0, 0)

        mock_products = MagicMock()
        mock_products.products = []

        result = await stats_report_data(mock_batch, mock_products)

        assert result.total_products == 0
        assert result.aggregated_products == 0
        assert result.unaggregated_products == 0
        assert result.percent_aggregated == 0.0
        assert result.avg_speed == 0.0

    async def test_stats_report_data_zero_duration(self):
        mock_batch = MagicMock()
        mock_batch.shift_start = datetime(2024, 1, 1, 8, 0, 0)
        mock_batch.shift_end = datetime(2024, 1, 1, 8, 0, 0)

        mock_products = MagicMock()
        mock_products.products = [MagicMock(is_aggregated=True)]

        result = await stats_report_data(mock_batch, mock_products)

        assert result.total_products == 1
        assert result.aggregated_products == 1
        assert result.unaggregated_products == 0
        assert result.percent_aggregated == 100.0
        assert result.avg_speed == 0.0

    async def test_stats_report_data_zero_aggregated(self):
        mock_batch = MagicMock()
        mock_batch.shift_start = datetime(2024, 1, 1, 8, 0, 0)
        mock_batch.shift_end = datetime(2024, 1, 1, 10, 0, 0)

        mock_products = MagicMock()
        mock_products.products = [
            MagicMock(is_aggregated=False),
            MagicMock(is_aggregated=False),
        ]

        result = await stats_report_data(mock_batch, mock_products)

        assert result.total_products == 2
        assert result.aggregated_products == 0
        assert result.unaggregated_products == 2
        assert result.percent_aggregated == 0.0
        assert result.avg_speed == 0.0

    async def test_stats_report_data_rounding(self):
        mock_batch = MagicMock()
        mock_batch.shift_start = datetime(2024, 1, 1, 8, 0, 0)
        mock_batch.shift_end = datetime(2024, 1, 1, 9, 30, 0)

        mock_products = MagicMock()
        mock_products.products = [
            MagicMock(is_aggregated=True),
            MagicMock(is_aggregated=True),
            MagicMock(is_aggregated=False),
        ]

        result = await stats_report_data(mock_batch, mock_products)

        assert result.total_products == 3
        assert result.aggregated_products == 2
        assert result.unaggregated_products == 1
        assert result.percent_aggregated == 66.67
        assert result.avg_speed == 1.33
