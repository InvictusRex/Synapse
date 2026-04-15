"""
A2A Authentication
FastAPI dependency for API key, Bearer token, and OAuth 2.0 support
"""
import os
from typing import Optional

from fastapi import Request, HTTPException


class AuthConfig:
    """Authentication configuration loaded from environment"""

    def __init__(self):
        # Load API keys from env (comma-separated)
        keys_str = os.environ.get("A2A_API_KEYS", "")
        self.api_keys: set[str] = {k.strip() for k in keys_str.split(",") if k.strip()}

        # Load bearer tokens from env (comma-separated)
        tokens_str = os.environ.get("A2A_BEARER_TOKENS", "")
        self.bearer_tokens: set[str] = {t.strip() for t in tokens_str.split(",") if t.strip()}

        # If no keys configured, use a default dev key
        if not self.api_keys and not self.bearer_tokens:
            self.api_keys = {"synapse-dev-key"}

        # OAuth stub
        self.oauth_enabled: bool = os.environ.get("A2A_OAUTH_ENABLED", "").lower() == "true"
        self.oauth_jwks_url: Optional[str] = os.environ.get("A2A_OAUTH_JWKS_URL")

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_keys or self.bearer_tokens or self.oauth_enabled)


# Global auth config instance
_auth_config: Optional[AuthConfig] = None


def get_auth_config() -> AuthConfig:
    """Get or create the global auth config"""
    global _auth_config
    if _auth_config is None:
        _auth_config = AuthConfig()
    return _auth_config


def reset_auth_config():
    """Reset auth config (for testing)"""
    global _auth_config
    _auth_config = None


async def verify_auth(request: Request) -> None:
    """
    FastAPI dependency that verifies authentication.
    Checks x-api-key header, then Authorization: Bearer header.
    Used as a dependency on protected endpoints.
    """
    config = get_auth_config()

    if not config.auth_enabled:
        return

    # Check x-api-key header
    api_key = request.headers.get("x-api-key")
    if api_key and api_key in config.api_keys:
        return

    # Check Authorization: Bearer <token>
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token in config.bearer_tokens:
            return

        # OAuth 2.0 JWT validation stub
        if config.oauth_enabled:
            if _validate_oauth_token(token, config):
                return

    raise HTTPException(status_code=401, detail="Unauthorized")


def _validate_oauth_token(token: str, config: AuthConfig) -> bool:
    """
    OAuth 2.0 JWT validation stub.
    In production, this would validate the JWT against JWKS endpoint.
    """
    # Stub: always returns False unless implemented
    # To implement: fetch JWKS from config.oauth_jwks_url,
    # validate JWT signature, expiry, issuer, audience
    return False
