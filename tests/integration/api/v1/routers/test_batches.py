import io
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

created_batch_id = None


@patch("app.domain.services.batch_service.redis_service", new_callable=AsyncMock)
class TestBatchCRUD:
    async def test_create_batches(self, mock_redis, async_client: AsyncClient):
        mock_redis.keys = AsyncMock(return_value=[])
        global created_batch_id

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
        data = response.json()
        assert "batches" in data
        assert len(data["batches"]) == 1
        assert data["batches"][0]["batch_number"] == 1001

        # Сохраняем ID для следующих тестов в этом классе
        created_batch_id = data["batches"][0]["id"]

    async def test_create_duplicate_batch_return_error(
        self, mock_redis, async_client: AsyncClient
    ):
        mock_redis.keys = AsyncMock(return_value=[])

        payload = {
            "batches": [
                {
                    "task_description": "Тест дубликатов",
                    "work_center_name": "Цех №2",
                    "work_center_identifier": "999",
                    "shift": "1",
                    "team": "Бригада Ух",
                    "batch_number": 777777,
                    "batch_date": "2026-08-01",
                    "nomenclature": "Дубликат-Продукт",
                    "ekn_code": "777",
                    "work_center_id": 999,
                    "shift_start": "2026-08-01T08:00:00",
                    "shift_end": "2026-08-01T20:00:00",
                }
            ]
        }

        first_response = await async_client.post("api/v1/batches", json=payload)
        assert first_response.status_code == 201
        second_response = await async_client.post("api/v1/batches", json=payload)
        assert second_response.status_code in [400, 409]

    async def test_get_batch(self, mock_redis, async_client: AsyncClient):
        assert created_batch_id is not None, "Партия не была создана в предыдущем тесте"

        response = await async_client.get(f"/api/v1/batches/{created_batch_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_batch_id
        assert data["batch_number"] == 1001

    async def test_update_batch(self, mock_redis, async_client: AsyncClient):
        assert created_batch_id is not None

        payload = {"is_closed": True}
        response = await async_client.patch(
            f"/api/v1/batches/{created_batch_id}", json=payload
        )

        assert response.status_code == 200
        assert response.json()["is_closed"] is True

    async def test_get_batch_not_found(self, mock_redis, async_client: AsyncClient):
        response = await async_client.get("/api/v1/batches/9999999")
        assert response.status_code == 404
        data = response.json()
        assert "detail"


class TestBatchBackgroundTasks:
    @patch("app.api.v1.routers.batches.aggregate_products_batch.delay")
    async def test_aggregate_products_async(
        self, mock_delay, async_client: AsyncClient
    ):
        payload = {"unique_codes": ["CODE1", "CODE2"]}
        mock_delay.return_value.id = "fake-task-id-123"

        response = await async_client.post(
            "/api/v1/batches/1/aggregate-async", json=payload
        )

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "fake-task-id-123"

        mock_delay.assert_called_once_with(1, ["CODE1", "CODE2"])

    @patch("app.api.v1.routers.batches.generate_batch_report.delay")
    async def test_batch_generate_report(self, mock_delay, async_client: AsyncClient):
        payload = {"format": "pdf", "email": "test@example.com"}
        mock_delay.return_value.id = "fake-report-task-id"

        response = await async_client.post("/api/v1/batches/1/reports", json=payload)

        assert response.status_code == 202
        mock_delay.assert_called_once_with(1, "pdf", "test@example.com")

    @patch("app.api.v1.routers.batches.export_batches_to_file.delay")
    async def test_export_batches(self, mock_delay, async_client: AsyncClient):
        payload = {"filters": {"is_closed": True}, "format_file": "excel"}
        mock_delay.return_value.id = "fake-export-task-id"

        response = await async_client.post("/api/v1/batches/export", json=payload)

        assert response.status_code == 202
        mock_delay.assert_called_once_with({"is_closed": True}, "excel")


class TestBatchFileOperations:
    @patch("app.api.v1.routers.batches.import_batches_from_file.delay")
    @patch("app.api.v1.routers.batches.storage_service.upload_stream")
    async def test_import_batches(
        self, mock_upload_stream, mock_delay, async_client: AsyncClient
    ):
        mock_delay.return_value.id = "fake-import-task-id"

        # Имитируем содержимое CSV файла в оперативной памяти
        fake_file_content = b"batch_number,date\n1001,2026-01-01"
        fake_file = io.BytesIO(fake_file_content)

        # Формат: "имя_поля_в_запросе": ("название_файла", содержимое, "mime-тип")
        files = {"file": ("test_import.csv", fake_file, "text/csv")}

        response = await async_client.post("/api/v1/batches/import", files=files)

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "fake-import-task-id"

        # Проверяем, что была попытка загрузить файл в MinIO и запустить задачу
        mock_upload_stream.assert_called_once()
        mock_delay.assert_called_once()

    async def test_import_batches_invalid_extension(self, async_client: AsyncClient):
        fake_file = io.BytesIO(b"fake image content")
        files = {"file": ("test_image.jpg", fake_file, "image/jpeg")}

        response = await async_client.post("/api/v1/batches/import", files=files)

        # Ожидаем ошибку бизнес-логики (обычно обрабатывается как 400 Bad Request)
        assert response.status_code == 400
