import pytest
from unittest.mock import MagicMock

from mlit_mcp.tools.clear_cache import (
    ClearCacheInput,
    ClearCacheTool,
)


@pytest.fixture
def mock_http_client():
    client = MagicMock()
    # Mock clear_cache method (which doesn't exist yet on real client)
    client.clear_cache = MagicMock()
    client.get_stats = MagicMock(return_value={"total_requests": 0})
    return client


@pytest.fixture
def tool(mock_http_client):
    return ClearCacheTool(mock_http_client)


@pytest.mark.asyncio
async def test_clear_cache_run(tool, mock_http_client):
    """Test clearing cache calls http_client.clear_cache()."""
    input_data = ClearCacheInput()

    result = await tool.run(input_data)

    mock_http_client.clear_cache.assert_called_once()
    assert result.status == "success"
    assert "Cache cleared" in result.message
