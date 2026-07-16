from unittest.mock import AsyncMock, patch

import pytest

from app.domain.services.export_service import BatchExportService


class TestBatchExportService:
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        with patch("app.domain.services.export_service.BatchRepository") as MockRepo:
            svc = BatchExportService(session=mock_session)
            svc.mock_repo = MockRepo.return_value
            svc.mock_repo.get_batches_for_export = AsyncMock()
            yield svc

    async def test_export_batches_excel_success(self, service):
        service.mock_repo.get_batches_for_export.return_value = ["batch1", "batch2"]

        with (
            patch(
                "app.domain.services.export_service.generate_batches_excel"
            ) as mock_excel,
            patch("app.domain.services.export_service.storage_service") as mock_storage,
            patch("app.domain.services.export_service.os.path.exists") as mock_exists,
            patch("app.domain.services.export_service.os.remove") as mock_remove,
            patch("app.domain.services.export_service.settings") as mock_settings,
        ):

            mock_excel.return_value = "/tmp/fake_export.xlsx"
            mock_storage.upload_file.return_value = "https://s3.fake/file.xlsx"
            mock_exists.return_value = True
            mock_settings.minio.bucket_exports = "test-bucket"

            result = await service.export_batches({"status": "done"}, "excel")

            service.mock_repo.get_batches_for_export.assert_called_once_with(
                {"status": "done"}
            )
            mock_excel.assert_called_once_with(["batch1", "batch2"])
            mock_storage.upload_file.assert_called_once_with(
                bucket="test-bucket",
                object_name="fake_export.xlsx",
                file_path="/tmp/fake_export.xlsx",
            )
            mock_remove.assert_called_once_with("/tmp/fake_export.xlsx")

            assert result["success"] is True
            assert result["file_url"] == "https://s3.fake/file.xlsx"
            assert result["total_batches"] == 2

    async def test_export_batches_csv_success(self, service):
        service.mock_repo.get_batches_for_export.return_value = ["batch1"]

        with (
            patch(
                "app.domain.services.export_service.generate_batches_csv"
            ) as mock_csv,
            patch("app.domain.services.export_service.storage_service") as mock_storage,
            patch("app.domain.services.export_service.os.path.exists") as mock_exists,
            patch("app.domain.services.export_service.os.remove") as mock_remove,
            patch("app.domain.services.export_service.settings") as mock_settings,
        ):

            mock_csv.return_value = "/tmp/fake_export.csv"
            mock_storage.upload_file.return_value = "https://s3.fake/file.csv"
            mock_exists.return_value = True
            mock_settings.minio.bucket_exports = "test-bucket"

            result = await service.export_batches({"status": "done"}, "csv")

            mock_csv.assert_called_once_with(["batch1"])
            mock_storage.upload_file.assert_called_once_with(
                bucket="test-bucket",
                object_name="fake_export.csv",
                file_path="/tmp/fake_export.csv",
            )
            mock_remove.assert_called_once_with("/tmp/fake_export.csv")

            assert result["success"] is True
            assert result["file_url"] == "https://s3.fake/file.csv"
            assert result["total_batches"] == 1

    async def test_export_batches_cleanup_on_exception(self, service):
        service.mock_repo.get_batches_for_export.return_value = ["batch1"]

        with (
            patch(
                "app.domain.services.export_service.generate_batches_excel"
            ) as mock_excel,
            patch("app.domain.services.export_service.storage_service") as mock_storage,
            patch("app.domain.services.export_service.os.path.exists") as mock_exists,
            patch("app.domain.services.export_service.os.remove") as mock_remove,
            patch("app.domain.services.export_service.settings") as mock_settings,
        ):

            mock_excel.return_value = "/tmp/fake_export.xlsx"
            mock_storage.upload_file.side_effect = Exception("S3 upload failed")
            mock_exists.return_value = True
            mock_settings.minio.bucket_exports = "test-bucket"

            with pytest.raises(Exception, match="S3 upload failed"):
                await service.export_batches({}, "excel")

            mock_remove.assert_called_once_with("/tmp/fake_export.xlsx")

    async def test_export_batches_no_cleanup_if_file_not_exists(self, service):
        service.mock_repo.get_batches_for_export.return_value = []

        with (
            patch(
                "app.domain.services.export_service.generate_batches_csv"
            ) as mock_csv,
            patch("app.domain.services.export_service.storage_service") as mock_storage,
            patch("app.domain.services.export_service.os.path.exists") as mock_exists,
            patch("app.domain.services.export_service.os.remove") as mock_remove,
            patch("app.domain.services.export_service.settings") as mock_settings,
        ):

            mock_csv.return_value = "/tmp/fake_export.csv"
            mock_storage.upload_file.return_value = "url"
            mock_exists.return_value = False
            mock_settings.minio.bucket_exports = "test-bucket"

            await service.export_batches({}, "csv")

            mock_exists.assert_called_once_with("/tmp/fake_export.csv")
            mock_remove.assert_not_called()
