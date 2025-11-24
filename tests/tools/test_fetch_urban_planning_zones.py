from __future__ import annotations

import pytest
from unittest.mock import AsyncMock
from pydantic import ValidationError

from mlit_mcp.http_client import FetchResult, MLITHttpClient
from mlit_mcp.tools.fetch_urban_planning_zones import (
    FetchUrbanPlanningZonesInput,
    FetchUrbanPlanningZonesTool,
)
from mlit_mcp.tools.gis_helpers import decode_base64_to_mvt


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock(spec=MLITHttpClient)
    return client


@pytest.fixture
def tool(mock_http_client):
    """Create a FetchUrbanPlanningZonesTool instance."""
    return FetchUrbanPlanningZonesTool(http_client=mock_http_client)


@pytest.fixture
def sample_geojson():
    """Sample GeoJSON data."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[139.7, 35.7], [139.8, 35.7], [139.8, 35.8], [139.7, 35.7]]]},
                "properties": {"zone": "residential"},
            }
        ],
    }


class TestFetchUrbanPlanningZonesInput:
    """Test input validation."""

    def test_valid_input_with_tiles(self):
        """Test valid input with z/x/y tiles."""
        payload = FetchUrbanPlanningZonesInput(
            area="13",
            z=10,
            x=100,
            y=200,
        )
        assert payload.z == 10
        assert payload.x == 100
        assert payload.y == 200
        assert payload.bbox is None

    def test_valid_input_with_bbox(self):
        """Test valid input with bounding box."""
        payload = FetchUrbanPlanningZonesInput(
            area="13",
            bbox="139.0,35.0,140.0,36.0",
        )
        assert payload.bbox == "139.0,35.0,140.0,36.0"
        assert payload.z is None

    def test_cannot_specify_both_tiles_and_bbox(self):
        """Test that specifying both tiles and bbox fails."""
        with pytest.raises(ValidationError) as exc_info:
            FetchUrbanPlanningZonesInput(
                area="13",
                z=10,
                x=100,
                y=200,
                bbox="139.0,35.0,140.0,36.0",
            )
        assert "Cannot specify both" in str(exc_info.value)

    def test_must_specify_either_tiles_or_bbox(self):
        """Test that not specifying either tiles or bbox fails."""
        with pytest.raises(ValidationError) as exc_info:
            FetchUrbanPlanningZonesInput(area="13")
        assert "Must specify either" in str(exc_info.value)

    def test_incomplete_tile_specification(self):
        """Test that incomplete tile specification fails."""
        with pytest.raises(ValidationError) as exc_info:
            FetchUrbanPlanningZonesInput(area="13", z=10, x=100)
        assert "must specify all of z, x, and y" in str(exc_info.value)


class TestFetchUrbanPlanningZonesTool:
    """Test FetchUrbanPlanningZonesTool functionality."""

    @pytest.mark.anyio
    async def test_tiles_request_geojson(self, tool, mock_http_client, sample_geojson):
        """Test tile request with GeoJSON format."""
        mock_http_client.fetch.return_value = FetchResult(
            data=sample_geojson,
            from_cache=False,
        )

        payload = FetchUrbanPlanningZonesInput(
            area="13",
            z=10,
            x=100,
            y=200,
            responseFormat="geojson",
        )
        result = await tool.run(payload)

        assert result.geojson == sample_geojson
        assert result.pbf_base64 is None
        assert result.meta.format == "geojson"

        # Verify correct params were sent
        call_args = mock_http_client.fetch.call_args
        assert call_args.kwargs["params"]["z"] == 10
        assert call_args.kwargs["params"]["x"] == 100
        assert call_args.kwargs["params"]["y"] == 200

    @pytest.mark.anyio
    async def test_bbox_request(self, tool, mock_http_client, sample_geojson):
        """Test bbox request."""
        mock_http_client.fetch.return_value = FetchResult(
            data=sample_geojson,
            from_cache=False,
        )

        payload = FetchUrbanPlanningZonesInput(
            area="13",
            bbox="139.0,35.0,140.0,36.0",
        )
        result = await tool.run(payload)

        assert result.geojson == sample_geojson

        # Verify bbox was sent
        call_args = mock_http_client.fetch.call_args
        assert call_args.kwargs["params"]["bbox"] == "139.0,35.0,140.0,36.0"

    @pytest.mark.anyio
    async def test_pbf_format(self, tool, mock_http_client, tmp_path):
        """Test PBF format response."""
        pbf_content = b"\x1a\x0btest data"
        pbf_file = tmp_path / "test.pbf"
        pbf_file.write_bytes(pbf_content)

        mock_http_client.fetch.return_value = FetchResult(
            data=None,
            file_path=pbf_file,
            from_cache=False,
        )

        payload = FetchUrbanPlanningZonesInput(
            area="13",
            z=10,
            x=100,
            y=200,
            responseFormat="pbf",
        )
        result = await tool.run(payload)

        assert result.geojson is None
        assert result.pbf_base64 is not None
        
        # Verify decoding
        decoded = decode_base64_to_mvt(result.pbf_base64)
        assert decoded == pbf_content
