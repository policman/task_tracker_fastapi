from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessLogicException, NotFoundException
from app.domain.services.product_service import ProductService


class TestProductService:

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        return redis

    @pytest.fixture
    def service(self, mock_session, mock_redis):
        with (
            patch("app.domain.services.product_service.ProductRepository") as MockRepo,
            patch("app.domain.services.product_service.WebhookService") as MockWebhook,
        ):
            svc = ProductService(session=mock_session, redis_client=mock_redis)

            svc.mock_repo = MockRepo.return_value
            svc.mock_repo.create_products = AsyncMock()
            svc.mock_repo.get_products_to_aggregate = AsyncMock()
            svc.mock_repo.aggregate_products_batch = AsyncMock()

            svc.mock_webhook = MockWebhook.return_value
            svc.mock_webhook.trigger_product_aggregated = AsyncMock()

            yield svc

    async def test_create_products_success(self, service, mock_session, mock_redis):
        products_data = [{"unique_code": "123", "batch_id": 1}]

        mock_product_1 = MagicMock(batch_id=1)
        mock_product_2 = MagicMock(batch_id=2)
        service.mock_repo.create_products.return_value = [
            mock_product_1,
            mock_product_2,
        ]

        result = await service.create_products(products_data)

        service.mock_repo.create_products.assert_called_once_with(products_data)
        mock_session.commit.assert_called_once()

        mock_redis.delete.assert_any_call("dashboard_stats")
        mock_redis.delete.assert_any_call("batch_detail:batch_id_1")
        mock_redis.delete.assert_any_call("batch_statistics:batch_id_2")

        assert result == [mock_product_1, mock_product_2]

    async def test_create_products_integrity_error(self, service, mock_session):
        service.mock_repo.create_products.side_effect = IntegrityError(
            statement="INSERT...", params={}, orig=Exception("FK violation")
        )

        with pytest.raises(NotFoundException) as exc_info:
            await service.create_products([{"unique_code": "123", "batch_id": 999}])

        mock_session.rollback.assert_called_once()
        assert exc_info.value.message == "Batch for creating product(s) not found"

    async def test_aggregate_batch_products_success(
        self, service, mock_session, mock_redis
    ):
        batch_id = 1
        unique_codes = ["code1", "code2"]

        mock_p1 = MagicMock(unique_code="code1", is_aggregated=False)
        mock_p2 = MagicMock(unique_code="code2", is_aggregated=False)
        service.mock_repo.get_products_to_aggregate.return_value = [mock_p1, mock_p2]

        service.mock_repo.aggregate_products_batch.return_value = 2

        result = await service.aggregate_batch_products(batch_id, unique_codes)

        service.mock_repo.aggregate_products_batch.assert_called_once_with(
            batch_id, ["code1", "code2"]
        )
        mock_session.commit.assert_called_once()

        service.mock_webhook.trigger_product_aggregated.assert_called_once()
        kwargs = service.mock_webhook.trigger_product_aggregated.call_args.kwargs
        assert kwargs["unique_codes"] == ["code1", "code2"]
        assert kwargs["batch_id"] == batch_id

        assert result["success"] is True
        assert result["total"] == 2
        assert result["aggregated"] == 2
        assert len(result["errors"]) == 0

    async def test_aggregate_batch_products_partial_success(
        self, service, mock_session
    ):
        batch_id = 1
        unique_codes = ["code1", "code2", "code_missing"]

        mock_p1 = MagicMock(unique_code="code1", is_aggregated=False)
        mock_p2 = MagicMock(unique_code="code2", is_aggregated=True)

        service.mock_repo.get_products_to_aggregate.return_value = [mock_p1, mock_p2]
        service.mock_repo.aggregate_products_batch.return_value = 1

        result = await service.aggregate_batch_products(batch_id, unique_codes)

        assert result["success"] is False
        assert result["total"] == 3
        assert result["aggregated"] == 1
        assert result["failed"] == 2
        assert result["updated_codes"] == ["code1"]

        reasons = [e["reason"] for e in result["errors"]]
        assert "not found in this batch" in reasons
        assert "already aggregated" in reasons

    async def test_aggregate_batch_products_empty_database(self, service):
        service.mock_repo.get_products_to_aggregate.return_value = []

        with pytest.raises(BusinessLogicException) as exc_info:
            await service.aggregate_batch_products(1, ["code1"])

        assert exc_info.value.message == "No products to aggregate"

    async def test_aggregate_batch_products_zero_aggregated(self, service):
        mock_p1 = MagicMock(unique_code="code1", is_aggregated=True)
        service.mock_repo.get_products_to_aggregate.return_value = [mock_p1]

        with pytest.raises(BusinessLogicException) as exc_info:
            await service.aggregate_batch_products(1, ["code1"])

        assert exc_info.value.message == "No one products was aggregated"
        assert "errors" in exc_info.value.payload
