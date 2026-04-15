"""
Tests for A2A Push Notifications
"""
import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from a2a.models import PushEvent, Task, WebhookRegistration
from a2a.push_notifications import PushNotificationDispatcher


@pytest.fixture
def dispatcher():
    return PushNotificationDispatcher()


class TestWebhookRegistration:

    def test_register_webhook(self, dispatcher):
        wh = WebhookRegistration(url="https://example.com/hook")
        wh_id = dispatcher.register(wh)
        assert len(wh_id) > 0
        assert dispatcher.get_webhook(wh_id) is not None

    def test_unregister_webhook(self, dispatcher):
        wh = WebhookRegistration(url="https://example.com/hook")
        wh_id = dispatcher.register(wh)
        assert dispatcher.unregister(wh_id) is True
        assert dispatcher.get_webhook(wh_id) is None

    def test_unregister_nonexistent(self, dispatcher):
        assert dispatcher.unregister("nonexistent") is False

    def test_list_webhooks(self, dispatcher):
        dispatcher.register(WebhookRegistration(url="https://a.com/hook"))
        dispatcher.register(WebhookRegistration(url="https://b.com/hook"))
        webhooks = dispatcher.list_webhooks()
        assert len(webhooks) == 2

    def test_register_with_secret(self, dispatcher):
        wh = WebhookRegistration(url="https://example.com/hook", secret="my-secret")
        wh_id = dispatcher.register(wh)
        stored = dispatcher.get_webhook(wh_id)
        assert stored.secret == "my-secret"

    def test_register_with_custom_events(self, dispatcher):
        wh = WebhookRegistration(url="https://example.com/hook", events=["task/completed"])
        wh_id = dispatcher.register(wh)
        stored = dispatcher.get_webhook(wh_id)
        assert stored.events == ["task/completed"]


class TestHMACSigning:

    def test_verify_valid_signature(self):
        payload = '{"event": "task/completed"}'
        secret = "my-secret"
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert PushNotificationDispatcher.verify_signature(payload, secret, f"sha256={sig}")

    def test_verify_invalid_signature(self):
        assert not PushNotificationDispatcher.verify_signature(
            "payload", "secret", "sha256=invalid"
        )

    def test_verify_malformed_signature(self):
        assert not PushNotificationDispatcher.verify_signature(
            "payload", "secret", "invalid-format"
        )


class TestPushDispatch:

    @pytest.mark.asyncio
    async def test_dispatch_matching_event(self, dispatcher):
        wh = WebhookRegistration(url="https://example.com/hook", events=["task/completed"])
        dispatcher.register(wh)

        task = Task()
        event = PushEvent(event="task/completed", task_id=task.id, task=task)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await dispatcher.dispatch(event)
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_non_matching_event(self, dispatcher):
        wh = WebhookRegistration(url="https://example.com/hook", events=["task/completed"])
        dispatcher.register(wh)

        task = Task()
        event = PushEvent(event="task/updated", task_id=task.id, task=task)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await dispatcher.dispatch(event)
            mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_with_hmac_signature(self, dispatcher):
        secret = "test-secret"
        wh = WebhookRegistration(url="https://example.com/hook", secret=secret)
        dispatcher.register(wh)

        task = Task()
        event = PushEvent(event="task/completed", task_id=task.id, task=task)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await dispatcher.dispatch(event)

            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert "X-Signature-256" in headers
            assert headers["X-Signature-256"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_dispatch_failure_does_not_raise(self, dispatcher):
        wh = WebhookRegistration(url="https://example.com/hook")
        dispatcher.register(wh)

        task = Task()
        event = PushEvent(event="task/completed", task_id=task.id, task=task)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            # Should not raise
            await dispatcher.dispatch(event)
