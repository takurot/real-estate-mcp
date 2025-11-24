from __future__ import annotations

import httpx
import pytest

from mlit_mcp.cache import BinaryFileCache, InMemoryTTLCache
from mlit_mcp.http_client import MLITHttpClient


class SequenceTransport:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if not self._responses:
            raise AssertionError("No more mocked responses available")
        self.requests.append(request)
        spec = self._responses.pop(0)
        status_code = spec["status_code"]
        if "json" in spec:
            return httpx.Response(status_code=status_code, json=spec["json"], headers=spec.get("headers"), request=request)
        return httpx.Response(status_code=status_code, content=spec.get("content", b""), headers=spec.get("headers"), request=request)


@pytest.mark.anyio
async def test_fetch_json_retries_on_retryable_status_and_caches(monkeypatch, tmp_path):
    monkeypatch.setenv("MLIT_API_KEY", "dummy")
    transport = SequenceTransport(
        [
            {"status_code": 429, "json": {"detail": "rate"}},
            {"status_code": 200, "json": {"items": [1, 2]}},
        ]
    )
    client = MLITHttpClient(
        base_url="https://example.test/",
        json_cache=InMemoryTTLCache(maxsize=4, ttl=60),
        file_cache=BinaryFileCache(tmp_path / "bin"),
        transport=httpx.MockTransport(transport),
    )

    result = await client.fetch("XIT001", params={"pref": "13"}, response_format="json")
    assert result.data == {"items": [1, 2]}
    assert result.from_cache is False
    assert len(transport.requests) == 2

    # Should hit cache without issuing another HTTP call
    cached = await client.fetch("XIT001", params={"pref": "13"}, response_format="json")
    assert cached.from_cache is True
    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_force_refresh_issues_new_request(monkeypatch, tmp_path):
    monkeypatch.setenv("MLIT_API_KEY", "dummy")
    transport = SequenceTransport(
        [
            {"status_code": 200, "json": {"value": 1}},
            {"status_code": 200, "json": {"value": 2}},
        ]
    )
    client = MLITHttpClient(
        base_url="https://example.test/",
        json_cache=InMemoryTTLCache(maxsize=4, ttl=60),
        file_cache=BinaryFileCache(tmp_path / "bin"),
        transport=httpx.MockTransport(transport),
    )

    first = await client.fetch("XIT002", params={"pref": "27"}, response_format="json")
    assert first.from_cache is False

    second = await client.fetch("XIT002", params={"pref": "27"}, response_format="json", force_refresh=True)
    assert second.data == {"value": 2}
    assert len(transport.requests) == 2


@pytest.mark.anyio
async def test_fetch_geojson_uses_file_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("MLIT_API_KEY", "dummy")
    transport = SequenceTransport(
        [
            {"status_code": 200, "content": b'{"type":"FeatureCollection","features":[]}'},
        ]
    )
    client = MLITHttpClient(
        base_url="https://example.test/",
        json_cache=InMemoryTTLCache(maxsize=4, ttl=60),
        file_cache=BinaryFileCache(tmp_path / "bin"),
        transport=httpx.MockTransport(transport),
    )

    result = await client.fetch("XKT001", params={"pref": "01"}, response_format="geojson")
    assert result.file_path is not None
    assert result.file_path.exists()
    assert result.from_cache is False

    cached = await client.fetch("XKT001", params={"pref": "01"}, response_format="geojson")
    assert cached.file_path == result.file_path
    assert cached.from_cache is True
    assert len(transport.requests) == 1

