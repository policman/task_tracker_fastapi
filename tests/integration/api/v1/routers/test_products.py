from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


@patch("app.core.cache.redis_service", new_callable=AsyncMock)
@patch("app.domain.services.batch_service.redis_service", new_callable=AsyncMock)
class TestProductCRUD:

    async def test_create_product_success(
        self, mock_batch_redis, mock_core_redis, async_client: AsyncClient
    ):
        mock_batch_redis.keys = AsyncMock(return_value=[])
        mock_core_redis.keys = AsyncMock(return_value=[])

        batch_payload = {
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

        batch_response = await async_client.post("/api/v1/batches", json=batch_payload)
        assert batch_response.status_code == 201

        product_payload = [
            {
                "unique_code": "test_uc",
                "batch_id": batch_response.json()["batches"][0]["id"],
            }
        ]

        product_response = await async_client.post(
            "/api/v1/products", json=product_payload
        )
        assert product_response.status_code == 201

    async def test_create_product_not_found_batch(
        self, mock_batch_redis, mock_core_redis, async_client: AsyncClient
    ):
        mock_batch_redis.keys = AsyncMock(return_value=[])
        mock_core_redis.keys = AsyncMock(return_value=[])

        payload = [
            {
                "unique_code": "test2_uc",
                "batch_id": 99999,
            }
        ]

        response = await async_client.post("/api/v1/products", json=payload)
        assert response.status_code == 404

    async def test_create_products_validation_error(
        self, mock_batch_redis, mock_core_redis, async_client: AsyncClient
    ):
        mock_batch_redis.keys = AsyncMock(return_value=[])
        mock_core_redis.keys = AsyncMock(return_value=[])

        payload = [{}]

        response = await async_client.post("/api/v1/products", json=payload)
        assert response.status_code == 422
