from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.domain.services.webhook_service import WebhookService


class TestWebhookService:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.add_all = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        with patch("app.domain.services.webhook_service.WebhookRepository") as MockRepo:
            svc = WebhookService(session=mock_session)
            svc.webhook_repo = MockRepo.return_value
            yield svc

    async def test_create_subscription(self, service, mock_session):
        data = {"url": "http://test.com", "secret_key": "secret"}
        service.webhook_repo.create = AsyncMock(return_value=MagicMock())

        await service.create_subscription(data)

        service.webhook_repo.create.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_trigger_event_sends_tasks(self, service, mock_session):
        mock_sub = MagicMock(id=1)
        mock_session.scalars = AsyncMock(return_value=MagicMock(all=lambda: [mock_sub]))

        mock_data = MagicMock()
        mock_data.model_dump.return_value = {"key": "val"}

        with patch("app.tasks.webhooks.send_webhook_delivery.apply_async") as mock_task:
            await service._trigger_event("batch_created", mock_data)

            assert mock_session.add.called
            await mock_session.flush()
            assert mock_task.called

    async def test_process_delivery_success(self, service, mock_session):
        mock_sub = MagicMock(secret_key="secret", url="http://hook.com", timeout=5.0)
        mock_delivery = MagicMock(
            subscription=mock_sub, payload={"test": "data"}, attempts=0
        )

        mock_session.scalars = AsyncMock(
            return_value=MagicMock(first=lambda: mock_delivery)
        )

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, text="ok")

            result = await service.process_delivery(1)

            assert result["success"] is True
            assert mock_delivery.status == "success"
            mock_session.commit.assert_called_once()

    async def test_process_delivery_failure_retry(self, service, mock_session):
        mock_sub = MagicMock(
            secret_key="secret", url="http://hook.com", timeout=5.0, retry_count=3
        )
        mock_delivery = MagicMock(
            subscription=mock_sub,
            payload={"test": "data"},
            attempts=1,
            status="pending",
        )

        mock_session.scalars = AsyncMock(
            return_value=MagicMock(first=lambda: mock_delivery)
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = mock_client_class.return_value.__aenter__.return_value
            mock_client.post.side_effect = httpx.ConnectError("Connection Error")

            result = await service.process_delivery(1)

            assert result["success"] is False
            assert mock_delivery.status == "failed"
            assert result["retry_exc"] is not None
            mock_session.commit.assert_called()

    async def test_trigger_events_bulk(self, service, mock_session):
        mock_sub = MagicMock(id=1)
        mock_session.scalars = AsyncMock(return_value=MagicMock(all=lambda: [mock_sub]))

        event1 = MagicMock()
        event1.model_dump.return_value = {"id": 1}
        event2 = MagicMock()
        event2.model_dump.return_value = {"id": 2}

        with patch("app.tasks.webhooks.send_webhook_delivery.apply_async") as mock_task:
            await service._trigger_events_bulk("batch_created", [event1, event2])

            assert mock_session.add_all.called
            assert mock_task.call_count == 2
