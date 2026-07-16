from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import BusinessLogicException
from app.tasks.aggregation import aggregate_batch_products


class TestAggregateBatchProductsTask:

    @patch("app.tasks.aggregation.ProductService")
    @patch("app.tasks.aggregation.RedisService")
    @patch("app.tasks.aggregation.DatabaseHelper")
    @patch.object(aggregate_batch_products, "update_state")
    def test_task_success(
        self,
        mock_update_state,
        mock_db_helper,
        mock_redis_service,
        mock_product_service,
    ):

        mock_db_instance = mock_db_helper.return_value
        mock_db_instance.dispose = AsyncMock()
        mock_session_factory = AsyncMock()
        mock_db_instance.session_factory.return_value = mock_session_factory

        mock_redis_instance = mock_redis_service.return_value
        mock_redis_instance.close = AsyncMock()

        mock_ps_instance = mock_product_service.return_value
        expected_result = {"success": True, "aggregated": 2}
        mock_ps_instance.aggregate_batch_products = AsyncMock(
            return_value=expected_result
        )

        batch_id = 1
        unique_codes = ["code1", "code2"]
        result = aggregate_batch_products(batch_id, unique_codes)

        # 3. ASSERT
        mock_update_state.assert_called_once_with(
            state="PROGRESS",
            meta={"current": 0, "total": 2, "progress": 0},
        )

        mock_ps_instance.aggregate_batch_products.assert_called_once_with(
            batch_id, unique_codes
        )
        assert result == expected_result

        mock_db_instance.dispose.assert_called_once()
        mock_redis_instance.close.assert_called_once()

    @patch("app.tasks.aggregation.ProductService")
    @patch("app.tasks.aggregation.RedisService")
    @patch("app.tasks.aggregation.DatabaseHelper")
    @patch.object(aggregate_batch_products, "update_state")
    def test_task_handles_business_logic_exception(
        self, mock_update_state, mock_db, mock_redis, mock_product_service
    ):
        mock_db.return_value.dispose = AsyncMock()
        mock_db.return_value.session_factory.return_value = AsyncMock()
        mock_redis.return_value.close = AsyncMock()

        mock_ps_instance = mock_product_service.return_value
        mock_ps_instance.aggregate_batch_products.side_effect = BusinessLogicException(
            message="No products to aggregate", payload={"errors": ["some error"]}
        )

        result = aggregate_batch_products(1, ["code1"])

        assert result == {
            "success": False,
            "message": "No products to aggregate",
            "errors": {"errors": ["some error"]},
        }
        mock_db.return_value.dispose.assert_called_once()
        mock_redis.return_value.close.assert_called_once()

    @patch("app.tasks.aggregation.ProductService")
    @patch("app.tasks.aggregation.RedisService")
    @patch("app.tasks.aggregation.DatabaseHelper")
    @patch.object(aggregate_batch_products, "retry")
    @patch.object(aggregate_batch_products, "update_state")
    def test_task_triggers_retry_on_unexpected_exception(
        self, mock_update_state, mock_retry, mock_db, mock_redis, mock_product_service
    ):
        mock_db.return_value.dispose = AsyncMock()
        mock_db.return_value.session_factory.return_value = AsyncMock()
        mock_redis.return_value.close = AsyncMock()

        class RetryException(Exception):
            pass

        mock_retry.side_effect = RetryException

        mock_ps_instance = mock_product_service.return_value
        mock_ps_instance.aggregate_batch_products.side_effect = Exception(
            "Database dead"
        )

        with pytest.raises(RetryException):
            aggregate_batch_products(1, ["code1"])

        mock_retry.assert_called_once()
        assert mock_retry.call_args.kwargs["countdown"] == 5

        mock_db.return_value.dispose.assert_called_once()
        mock_redis.return_value.close.assert_called_once()
