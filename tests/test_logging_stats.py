import pytest
from mlit_mcp.http_client import MLITHttpClient, RetryableHTTPStatusError
from mlit_mcp.cache import InMemoryTTLCache, BinaryFileCache
import logging


@pytest.fixture
def http_client(tmp_path):
    return MLITHttpClient(
        base_url="http://test.api",
        json_cache=InMemoryTTLCache(maxsize=10, ttl=60),
        file_cache=BinaryFileCache(directory=tmp_path / "cache"),
        api_key="test_key",
    )


@pytest.mark.asyncio
async def test_initial_stats(http_client):
    stats = http_client.get_stats()
    assert stats["total_requests"] == 0
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0
    assert stats["api_errors"] == 0


@pytest.mark.asyncio
async def test_stats_cache_miss(http_client, httpx_mock):
    httpx_mock.add_response(json={"data": "test"})

    await http_client.fetch("http://test.api/data")

    stats = http_client.get_stats()
    assert stats["total_requests"] == 1
    assert stats["cache_misses"] == 1
    assert stats["cache_hits"] == 0


@pytest.mark.asyncio
async def test_stats_cache_hit(http_client, httpx_mock):
    httpx_mock.add_response(json={"data": "test"})

    # First request - miss
    await http_client.fetch("http://test.api/data")

    # Second request - hit
    await http_client.fetch("http://test.api/data")

    stats = http_client.get_stats()
    assert stats["total_requests"] == 2
    assert stats["cache_misses"] == 1
    assert stats["cache_hits"] == 1


@pytest.mark.asyncio
async def test_stats_api_error(http_client, httpx_mock):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    # It retries 4 times by default then raises

    with pytest.raises(RetryableHTTPStatusError):
        await http_client.fetch("http://test.api/error")

    stats = http_client.get_stats()
    # It might count as 1 request that failed
    assert stats["api_errors"] == 1


@pytest.mark.asyncio
async def test_logging_requests(http_client, httpx_mock, caplog):
    caplog.set_level(logging.INFO)
    httpx_mock.add_response(json={"data": "test"})

    await http_client.fetch("http://test.api/logging")

    assert "Fetching http://test.api/logging" in caplog.text
    assert "Cache miss" in caplog.text


@pytest.mark.asyncio
async def test_logging_cache_hit(http_client, httpx_mock, caplog):
    caplog.set_level(logging.INFO)
    httpx_mock.add_response(json={"data": "test"})

    # Populate cache
    await http_client.fetch("http://test.api/hit")
    caplog.clear()

    # Hit cache
    await http_client.fetch("http://test.api/hit")

    assert "Cache hit" in caplog.text


@pytest.mark.asyncio
async def test_logging_api_error(http_client, httpx_mock, caplog):
    caplog.set_level(logging.ERROR)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)

    with pytest.raises(RetryableHTTPStatusError):
        await http_client.fetch("http://test.api/error_log")

    # Expect error log about the failure
    assert "Request failed" in caplog.text


@pytest.mark.asyncio
async def test_force_refresh_stats(http_client, httpx_mock):
    httpx_mock.add_response(json={"data": "test"})
    httpx_mock.add_response(json={"data": "test"})  # For second call

    # First request - cache it
    await http_client.fetch("http://test.api/force", force_refresh=False)

    # Second request - force refresh (should be miss even if in cache)
    await http_client.fetch("http://test.api/force", force_refresh=True)

    stats = http_client.get_stats()
    assert stats["total_requests"] == 2
    assert (
        stats["cache_hits"] == 0
    )  # First was miss (empty), second was force (skipped cache)
    assert stats["cache_misses"] == 2
