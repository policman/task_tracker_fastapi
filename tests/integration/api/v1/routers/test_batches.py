import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
async def sample_batch(async_client: AsyncClient):
    payload = {
        "batches": [
            {
                "task_description": "test",
                "work_center_name": "Цех №1",
                "work_center_identifier": "123",
                "shift": "test",
                "team": "testovaya",
                "batch_number": 9999,
                "batch_date": "2026-07-15",
                "nomenclature": "Test Product А",
                "ekn_code": "123",
                "work_center_id": 123,
                "shift_start": "2026-07-15T08:00:00",
                "shift_end": "2026-07-15T20:00:00",
            }
        ]
    }
    response = await async_client.post("/api/v1/batches", json=payload)
    return response.json()["batches"][0]


@patch("app.domain.services.batch_service.redis_service", new_callable=AsyncMock)
class TestBatchCRUD:
    async def test_create_batches(self, mock_redis, async_client: AsyncClient):
        mock_redis.keys = AsyncMock(return_value=[])
        payload = {
            "batches": [
                {
                    "task_description": "test",
                    "work_center_name": "Цех №1",
                    "work_center_identifier": "123",
                    "shift": "test",
                    "team": "testovaya",
                    "batch_number": 1001,
                    "batch_date": "2026-07-15",
                    "nomenclature": "Test Product А",
                    "ekn_code": "123",
                    "work_center_id": 123,
                    "shift_start": "2026-07-15T08:00:00",
                    "shift_end": "2026-07-15T20:00:00",
                }
            ]
        }
        response = await async_client.post("/api/v1/batches", json=payload)
        assert response.status_code == 201

    async def test_create_duplicate_batch_return_error(
        self, mock_redis, async_client: AsyncClient
    ):
        mock_redis.keys = AsyncMock(return_value=[])
        payload = {
            "batches": [
                {
                    "task_description": "Дубликат",
                    "work_center_name": "Цех №2",
                    "work_center_identifier": "999",
                    "shift": "1",
                    "team": "Бригада",
                    "batch_number": 777777,
                    "batch_date": "2026-08-01",
                    "nomenclature": "Дубликат",
                    "ekn_code": "777",
                    "work_center_id": 999,
                    "shift_start": "2026-08-01T08:00:00",
                    "shift_end": "2026-08-01T20:00:00",
                }
            ]
        }
        await async_client.post("api/v1/batches", json=payload)
        second_response = await async_client.post("api/v1/batches", json=payload)
        assert second_response.status_code in [400, 409]

    async def test_get_batch(self, mock_redis, async_client: AsyncClient, sample_batch):
        batch_id = sample_batch["id"]
        response = await async_client.get(f"/api/v1/batches/{batch_id}")
        assert response.status_code == 200
        assert response.json()["id"] == batch_id

    async def test_update_batch(
        self, mock_redis, async_client: AsyncClient, sample_batch
    ):
        batch_id = sample_batch["id"]
        payload = {"is_closed": True}
        response = await async_client.patch(f"/api/v1/batches/{batch_id}", json=payload)
        assert response.status_code == 200
        assert response.json()["is_closed"] is True

    async def test_get_batch_not_found(self, mock_redis, async_client: AsyncClient):
        response = await async_client.get("/api/v1/batches/9999999")
        assert response.status_code == 404


class TestBatchBackgroundTasks:
    @patch("app.api.v1.routers.batches.aggregate_batch_products.delay")
    async def test_aggregate_products_async(
        self, mock_delay, async_client: AsyncClient
    ):
        mock_delay.return_value.id = "fake-task-id-123"
        response = await async_client.post(
            "/api/v1/batches/1/aggregate-async", json={"unique_codes": ["CODE1"]}
        )
        assert response.status_code == 202
        assert mock_delay.called

    @patch("app.api.v1.routers.batches.generate_batch_report.delay")
    async def test_batch_generate_report(self, mock_delay, async_client: AsyncClient):
        mock_delay.return_value.id = "fake-report-task-id"
        response = await async_client.post(
            "/api/v1/batches/1/reports",
            json={"format": "pdf", "email": "test@example.com"},
        )
        assert response.status_code == 202

    @patch("app.api.v1.routers.batches.export_batches_to_file.delay")
    async def test_export_batches(self, mock_delay, async_client: AsyncClient):
        mock_delay.return_value.id = "fake-export-task-id"
        response = await async_client.post(
            "/api/v1/batches/export", json={"filters": {}, "format_file": "excel"}
        )
        assert response.status_code == 202


class TestBatchFileOperations:
    @patch("app.api.v1.routers.batches.import_batches_from_file.delay")
    @patch("app.api.v1.routers.batches.storage_service.upload_stream")
    async def test_import_batches(
        self, mock_upload, mock_delay, async_client: AsyncClient
    ):
        mock_delay.return_value.id = "fake-import-task-id"
        files = {
            "file": (
                "test.csv",
                io.BytesIO(b"batch_number,date\n1001,2026-01-01"),
                "text/csv",
            )
        }
        response = await async_client.post("/api/v1/batches/import", files=files)
        assert response.status_code == 202

    async def test_import_batches_invalid_extension(self, async_client: AsyncClient):
        files = {"file": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")}
        response = await async_client.post("/api/v1/batches/import", files=files)
        assert response.status_code == 400
