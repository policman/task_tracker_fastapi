from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.services.import_service import BatchImportService


class TestBatchImportService:
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        with (
            patch("app.domain.services.import_service.BatchRepository") as MockRepo,
            patch("app.domain.services.import_service.WebhookService") as MockWebhook,
        ):
            svc = BatchImportService(session=mock_session)
            svc.mock_repo = MockRepo.return_value
            svc.mock_webhook = MockWebhook.return_value

            svc.mock_webhook.trigger_batches_created_bulk = AsyncMock()
            svc.mock_webhook.trigger_import_completed = AsyncMock()

            yield svc

    async def test_import_batches_csv_success(self, service):
        with (
            patch("app.domain.services.import_service.storage_service"),
            patch(
                "app.domain.services.import_service.parse_csv_generator"
            ) as mock_parser,
            patch("app.domain.services.import_service.BatchCreate") as mock_schema,
            patch(
                "app.domain.services.import_service.os.path.exists", return_value=True
            ),
            patch("app.domain.services.import_service.os.remove"),
        ):

            mock_parser.return_value = [
                (2, {"batch_number": "1", "batch_date": "2024-01-01"})
            ]
            mock_schema.model_validate.return_value = MagicMock(
                batch_number="1", batch_date="2024-01-01"
            )
            service.mock_repo.exists_by_number_date = AsyncMock(return_value=False)
            service.mock_repo.create = AsyncMock(return_value=MagicMock())

            result = await service.import_batches("test.csv")

            assert result["success"] is True
            assert result["created"] == 1
            service.mock_webhook.trigger_import_completed.assert_called_once()

    async def test_import_batches_skip_if_exists(self, service):
        with (
            patch("app.domain.services.import_service.storage_service"),
            patch(
                "app.domain.services.import_service.parse_csv_generator"
            ) as mock_parser,
            patch("app.domain.services.import_service.BatchCreate") as mock_schema,
            patch(
                "app.domain.services.import_service.os.path.exists", return_value=True
            ),
            patch("app.domain.services.import_service.os.remove"),
        ):

            mock_parser.return_value = [
                (2, {"batch_number": "1", "batch_date": "2024-01-01"})
            ]
            mock_schema.model_validate.return_value = MagicMock(
                batch_number="1", batch_date="2024-01-01"
            )
            service.mock_repo.exists_by_number_date = AsyncMock(return_value=True)

            result = await service.import_batches("test.csv")

            assert result["created"] == 0
            assert result["skipped"] == 1

    async def test_import_batches_validation_error(self, service):
        with (
            patch("app.domain.services.import_service.storage_service"),
            patch(
                "app.domain.services.import_service.parse_csv_generator"
            ) as mock_parser,
            patch(
                "app.domain.services.import_service.os.path.exists", return_value=True
            ),
            patch("app.domain.services.import_service.os.remove"),
        ):

            mock_parser.return_value = [(2, {"invalid": "data"})]

            result = await service.import_batches("test.csv")

            assert result["created"] == 0
            assert result["skipped"] == 1
            assert len(result["errors"]) == 1

    async def test_import_batches_invalid_extension(self, service):
        with (
            patch("app.domain.services.import_service.storage_service"),
            patch(
                "app.domain.services.import_service.os.path.exists", return_value=False
            ),
        ):
            with pytest.raises(ValueError, match="Supported files: xlsx or csv"):
                await service.import_batches("test.txt")

    async def test_import_batches_bulk_trigger(self, service):
        with (
            patch("app.domain.services.import_service.storage_service"),
            patch(
                "app.domain.services.import_service.parse_csv_generator"
            ) as mock_parser,
            patch("app.domain.services.import_service.BatchCreate") as mock_schema,
            patch(
                "app.domain.services.import_service.os.path.exists", return_value=True
            ),
            patch("app.domain.services.import_service.os.remove"),
        ):

            mock_parser.return_value = [
                (i, {"batch_number": str(i), "batch_date": "2024-01-01"})
                for i in range(2, 102)
            ]
            mock_schema.model_validate.return_value = MagicMock(
                batch_number=1, batch_date="2024-01-01"
            )
            service.mock_repo.exists_by_number_date = AsyncMock(return_value=False)
            service.mock_repo.create = AsyncMock(return_value=MagicMock())

            await service.import_batches("test.csv")

            assert service.mock_webhook.trigger_batches_created_bulk.call_count >= 1
