"""
Test configuration and shared fixtures for Synapse test suite
"""
import os
import sys
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set a dummy API key for tests that don't actually call the API
os.environ.setdefault("GROQ_API_KEY", "test-api-key-for-testing")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test file operations"""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_groq():
    """Mock the Groq API client to avoid real API calls"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "mocked response"}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("groq.Groq", return_value=mock_client) as mock_cls:
        mock_cls._client = mock_client
        mock_cls._response = mock_response
        yield mock_cls


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset MCP server and A2A bus singletons between tests"""
    import mcp.server as mcp_mod
    import core.a2a_bus as bus_mod

    mcp_mod._mcp_instance = None
    bus_mod._bus_instance = None
    yield
    mcp_mod._mcp_instance = None
    bus_mod._bus_instance = None
