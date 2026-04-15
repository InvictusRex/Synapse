"""
Tests for A2A Authentication
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from a2a.auth import AuthConfig, get_auth_config, reset_auth_config, verify_auth


@pytest.fixture(autouse=True)
def reset_auth():
    """Reset auth config between tests"""
    reset_auth_config()
    yield
    reset_auth_config()


class TestAuthConfig:

    def test_default_dev_key(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "", "A2A_BEARER_TOKENS": ""}, clear=False):
            config = AuthConfig()
            assert "synapse-dev-key" in config.api_keys

    def test_custom_api_keys(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "key1,key2,key3", "A2A_BEARER_TOKENS": ""}, clear=False):
            config = AuthConfig()
            assert "key1" in config.api_keys
            assert "key2" in config.api_keys
            assert "key3" in config.api_keys
            assert "synapse-dev-key" not in config.api_keys

    def test_bearer_tokens(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "k", "A2A_BEARER_TOKENS": "token1,token2"}, clear=False):
            config = AuthConfig()
            assert "token1" in config.bearer_tokens
            assert "token2" in config.bearer_tokens

    def test_oauth_disabled_by_default(self):
        config = AuthConfig()
        assert config.oauth_enabled is False

    def test_oauth_enabled(self):
        with patch.dict(os.environ, {"A2A_OAUTH_ENABLED": "true"}, clear=False):
            config = AuthConfig()
            assert config.oauth_enabled is True

    def test_auth_enabled(self):
        config = AuthConfig()
        assert config.auth_enabled is True


class TestVerifyAuth:

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "test-key", "A2A_BEARER_TOKENS": ""}, clear=False):
            reset_auth_config()
            request = MagicMock()
            request.headers = {"x-api-key": "test-key"}
            await verify_auth(request)  # Should not raise

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "correct-key", "A2A_BEARER_TOKENS": ""}, clear=False):
            reset_auth_config()
            request = MagicMock()
            request.headers = {"x-api-key": "wrong-key"}
            with pytest.raises(HTTPException) as exc_info:
                await verify_auth(request)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_bearer_token(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "", "A2A_BEARER_TOKENS": "my-token"}, clear=False):
            reset_auth_config()
            request = MagicMock()
            request.headers = {"authorization": "Bearer my-token", "x-api-key": ""}
            await verify_auth(request)  # Should not raise

    @pytest.mark.asyncio
    async def test_invalid_bearer_token(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "", "A2A_BEARER_TOKENS": "correct-token"}, clear=False):
            reset_auth_config()
            request = MagicMock()
            request.headers = {"authorization": "Bearer wrong-token", "x-api-key": ""}
            with pytest.raises(HTTPException):
                await verify_auth(request)

    @pytest.mark.asyncio
    async def test_no_auth_header(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "key", "A2A_BEARER_TOKENS": ""}, clear=False):
            reset_auth_config()
            request = MagicMock()
            request.headers = {}
            with pytest.raises(HTTPException):
                await verify_auth(request)

    @pytest.mark.asyncio
    async def test_default_dev_key_works(self):
        with patch.dict(os.environ, {"A2A_API_KEYS": "", "A2A_BEARER_TOKENS": ""}, clear=False):
            reset_auth_config()
            request = MagicMock()
            request.headers = {"x-api-key": "synapse-dev-key"}
            await verify_auth(request)  # Should not raise
