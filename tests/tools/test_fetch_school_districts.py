from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from pydantic import ValidationError

from mlit_mcp.http_client import FetchResult, MLITHttpClient
from mlit_mcp.tools.fetch_school_districts import FetchSchoolDistrictsInput, FetchSchoolDistrictsTool
from mlit_mcp.tools.gis_helpers import decode_base64_to_mvt


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock(spec=MLITHttpClient)
    return client


@pytest.fixture
def tool(mock_http_client):
    """Create a FetchSchoolDistrictsTool instance."""
    return FetchSchoolDistrictsTool(http_client=mock_http_client)


class TestFetchSchoolDistrictsInput:
    """Test input validation."""

    def test_valid_input(self):
        """Test valid input."""
        payload = FetchSchoolDistrictsInput(
            area="13",
            z=10,
            x=100,
            y=200,
        )
        assert payload.area == "13"
        assert payload.z == 10
        assert payload.x == 100
        assert payload.y == 200
        assert payload.crs is None

    def test_valid_input_with_crs(self):
        """Test valid input with CRS."""
        payload = FetchSchoolDistrictsInput(
            area="13",
            z=10,
            x=100,
            y=200,
            crs="EPSG:4326",
        )
        assert payload.crs == "EPSG:4326"

    def test_invalid_crs(self):
        """Test that invalid CRS fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            FetchSchoolDistrictsInput(
                area="13",
                z=10,
                x=100,
                y=200,
                crs="INVALID",
            )
        assert "Invalid CRS code" in str(exc_info.value)

    def test_valid_crs_formats(self):
        """Test various valid CRS formats."""
        # EPSG format
        payload1 = FetchSchoolDistrictsInput(area="13", z=10, x=100, y=200, crs="EPSG:4326")
        assert payload1.crs == "EPSG:4326"
        
        # CRS format
        payload2 = FetchSchoolDistrictsInput(area="13", z=10, x=100, y=200, crs="CRS:84")
        assert payload2.crs == "CRS:84"


class TestFetchSchoolDistrictsTool:
    """Test FetchSchoolDistrictsTool functionality."""

    @pytest.mark.anyio
    async def test_mvt_base64_return(self, tool, mock_http_client, tmp_path):
        """Test MVT base64 encoding."""
        mvt_content = b"\x1a\x0eschool district data"
        mvt_file = tmp_path / "test.mvt"
        mvt_file.write_bytes(mvt_content)

        mock_http_client.fetch.return_value = FetchResult(
            data=None,
            file_path=mvt_file,
            from_cache=False,
        )

        payload = FetchSchoolDistrictsInput(
            area="13",
            z=10,
            x=100,
            y=200,
        )
        result = await tool.run(payload)

        assert result.mvt_base64 is not None
        assert result.meta.cache_hit is False
        
        # Verify we can decode it back
        decoded = decode_base64_to_mvt(result.mvt_base64)
        assert decoded == mvt_content

    @pytest.mark.anyio
    async def test_with_crs(self, tool, mock_http_client, tmp_path):
        """Test request with CRS parameter."""
        mvt_content = b"\x1a\x04test"
        mvt_file = tmp_path / "test.mvt"
        mvt_file.write_bytes(mvt_content)

        mock_http_client.fetch.return_value = FetchResult(
            data=None,
            file_path=mvt_file,
            from_cache=False,
        )

        payload = FetchSchoolDistrictsInput(
            area="13",
            z=10,
            x=100,
            y=200,
            crs="EPSG:4326",
        )
        result = await tool.run(payload)

        assert result.meta.crs == "EPSG:4326"
        
        # Verify CRS was passed to API
        call_args = mock_http_client.fetch.call_args
        assert call_args.kwargs["params"]["crs"] == "EPSG:4326"

    @pytest.mark.anyio
    async def test_cache_hit(self, tool, mock_http_client, tmp_path):
        """Test cache hit behavior."""
        mvt_content = b"\x1a\x04test"
        mvt_file = tmp_path / "test.mvt"
        mvt_file.write_bytes(mvt_content)

        mock_http_client.fetch.return_value = FetchResult(
            data=None,
            file_path=mvt_file,
            from_cache=True,
        )

        payload = FetchSchoolDistrictsInput(
            area="13",
            z=10,
            x=100,
            y=200,
        )
        result = await tool.run(payload)

        assert result.meta.cache_hit is True

    @pytest.mark.anyio
    async def test_force_refresh(self, tool, mock_http_client, tmp_path):
        """Test force_refresh parameter."""
        mvt_content = b"\x1a\x04test"
        mvt_file = tmp_path / "test.mvt"
        mvt_file.write_bytes(mvt_content)

        mock_http_client.fetch.return_value = FetchResult(
            data=None,
            file_path=mvt_file,
            from_cache=False,
        )

        payload = FetchSchoolDistrictsInput(
            area="13",
            z=10,
            x=100,
            y=200,
            forceRefresh=True,
        )
        await tool.run(payload)

        call_args = mock_http_client.fetch.call_args
        assert call_args.kwargs["force_refresh"] is True
