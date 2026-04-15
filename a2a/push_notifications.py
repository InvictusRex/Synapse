"""
A2A Push Notifications
Webhook registry and HMAC-signed event dispatch
"""
import hashlib
import hmac
import logging
import uuid
from typing import Optional

from a2a.models import PushEvent, WebhookRegistration

logger = logging.getLogger(__name__)


class PushNotificationDispatcher:
    """
    Manages webhook registrations and dispatches push notifications.
    Signs payloads with HMAC-SHA256 when a secret is provided.
    """

    def __init__(self):
        self._webhooks: dict[str, WebhookRegistration] = {}

    def register(self, registration: WebhookRegistration) -> str:
        """Register a webhook. Returns the webhook ID."""
        webhook_id = str(uuid.uuid4())[:8]
        self._webhooks[webhook_id] = registration
        return webhook_id

    def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook. Returns True if found and removed."""
        return self._webhooks.pop(webhook_id, None) is not None

    def get_webhook(self, webhook_id: str) -> Optional[WebhookRegistration]:
        """Get a webhook by ID"""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self) -> dict[str, WebhookRegistration]:
        """List all registered webhooks"""
        return dict(self._webhooks)

    async def dispatch(self, event: PushEvent) -> None:
        """
        Dispatch a push event to all matching webhooks.
        Non-blocking — failures are logged but don't raise.
        """
        import httpx

        payload = event.model_dump_json()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for wh_id, wh in self._webhooks.items():
                if event.event not in wh.events:
                    continue

                headers = {"Content-Type": "application/json"}

                # HMAC signing
                if wh.secret:
                    signature = hmac.new(
                        wh.secret.encode("utf-8"),
                        payload.encode("utf-8"),
                        hashlib.sha256,
                    ).hexdigest()
                    headers["X-Signature-256"] = f"sha256={signature}"

                try:
                    response = await client.post(
                        wh.url, content=payload, headers=headers
                    )
                    logger.debug(
                        f"Push to {wh.url}: {response.status_code}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Push notification failed for webhook {wh_id} "
                        f"({wh.url}): {e}"
                    )

    @staticmethod
    def verify_signature(payload: str, secret: str, signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature of a webhook payload.
        Useful for clients receiving push notifications.
        """
        if not signature.startswith("sha256="):
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
