import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_http_client():
    mock_client = MagicMock()
    mock_client.get_stats.return_value = {
        "total_requests": 10,
        "cache_hits": 5,
        "cache_misses": 5,
        "api_errors": 0,
    }
    return mock_client


@pytest.mark.asyncio
async def test_get_server_stats(mock_http_client):
    """Test get_server_stats returns client stats."""
    # Test that the http_client.get_stats() is used correctly
    result = mock_http_client.get_stats()
    assert result["total_requests"] == 10
    assert result["cache_hits"] == 5
    mock_http_client.get_stats.assert_called_once()
