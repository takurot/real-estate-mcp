import pytest
from unittest.mock import MagicMock
from mlit_mcp.mcp_server import get_server_stats

# We need to mock _get_http_client to return a mock client or ensure it works.
# But mcp_server.py imports types.


@pytest.fixture
def mock_http_client(monkeypatch):
    mock_client = MagicMock()
    mock_client.get_stats.return_value = {"test": 123}

    # We can't easily patch _get_http_client because it's in the module scope
    # and uses a global variable.
    # We patch the global variable _http_client in mcp_server module.

    monkeypatch.setattr("mlit_mcp.mcp_server._http_client", mock_client)
    # Also patch _get_http_client to return it, just in case
    # But verifying logic: if server uses _get_http_client(),
    # it initializes only if None. If we set it, it returns it.

    return mock_client


@pytest.mark.asyncio
async def test_get_server_stats(mock_http_client):
    result = await get_server_stats.fn()
    assert result == {"test": 123}
    mock_http_client.get_stats.assert_called_once()
