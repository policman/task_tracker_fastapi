from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_webhook_service
from app.main import app

client = TestClient(app)


class TestWebhookRouter:
    @pytest.fixture
    def mock_webhook_service(self):
        service = AsyncMock()
        app.dependency_overrides[get_webhook_service] = lambda: service
        yield service
        app.dependency_overrides.clear()

    def test_create_subscription(self, mock_webhook_service):
        payload = {
            "url": "https://hook.site/123",
            "events": ["batch_created"],
            "secret_key": "secret123",
        }

        mock_webhook_service.create_subscription.return_value = {
            "id": 1,
            "url": "https://hook.site/123",
            "events": ["batch_created"],
            "is_active": True,
            "created_at": "2026-07-16T07:00:00Z",
        }

        response = client.post("/api/v1/webhooks/", json=payload)

        if response.status_code == 422:
            print(response.json())

        assert response.status_code == 201
        assert response.json()["id"] == 1

    def test_get_subscriptions(self, mock_webhook_service):
        mock_webhook_service.get_subscriptions.return_value = [
            {
                "id": 1,
                "url": "https://hook.site/123",
                "events": ["batch_created"],
                "is_active": True,
                "created_at": "2026-07-16T07:00:00Z",
            }
        ]

        response = client.get("/api/v1/webhooks/")

        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_webhook_service.get_subscriptions.assert_called_once()

    def test_update_subscription(self, mock_webhook_service):
        payload = {"url": "https://new-url.com"}
        mock_webhook_service.update_subscription.return_value = {
            "id": 1,
            "url": "https://new-url.com/",
            "events": ["batch_created"],
            "is_active": True,
            "created_at": "2026-07-16T07:00:00Z",
        }

        response = client.patch("/api/v1/webhooks/1", json=payload)

        assert response.status_code == 200
        assert response.json()["url"] == "https://new-url.com/"

    def test_delete_subscription(self, mock_webhook_service):
        response = client.delete("/api/v1/webhooks/1")
        assert response.status_code == 204
        mock_webhook_service.delete_subscription.assert_called_once_with(1)

    def test_get_webhook_deliveries(self, mock_webhook_service):
        mock_webhook_service.get_webhook_deliveries.return_value = [
            {
                "id": 1,
                "status": "success",
                "event_type": "batch_created",
                "attempts": 1,
                "created_at": "2026-07-16T07:00:00Z",
            }
        ]

        response = client.get("/api/v1/webhooks/1/deliveries?limit=10&offset=0")

        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_webhook_service.get_webhook_deliveries.assert_called_once_with(1, 10, 0)
