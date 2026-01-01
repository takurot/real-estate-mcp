import pytest
from unittest.mock import AsyncMock

from mlit_mcp.tools.get_price_distribution import (
    GetPriceDistributionInput,
    GetPriceDistributionTool,
)
from mlit_mcp.tools.summarize_transactions import SummarizeTransactionsResponse


@pytest.fixture
def mock_http_client():
    return AsyncMock()


@pytest.fixture
def tool(mock_http_client):
    return GetPriceDistributionTool(mock_http_client)


def create_mock_summary(
    record_count: int = 100,
    avg_price: int = 100000000,
    min_price: int = 50000000,
    max_price: int = 200000000,
    percentile_25: int = 70000000,
    percentile_75: int = 130000000,
):
    """Helper to create mock summary response."""
    return SummarizeTransactionsResponse(
        recordCount=record_count,
        averagePrice=avg_price,
        medianPrice=avg_price,
        minPrice=min_price,
        maxPrice=max_price,
        percentile25=percentile_25,
        percentile75=percentile_75,
        priceByYear={"2020": avg_price},
        countByYear={"2020": record_count},
        typeDistribution={"中古マンション等": record_count},
        meta={"cacheHit": False, "dataset": "XIT001", "source": "test"},
    )


@pytest.mark.asyncio
async def test_get_price_distribution_basic(tool, mock_http_client):
    """Test basic price distribution generation."""
    mock_summary = create_mock_summary()
    tool._summarize_tool.run = AsyncMock(return_value=mock_summary)

    input_data = GetPriceDistributionInput(
        fromYear=2020,
        toYear=2021,
        area="13103",
        numBins=5,
    )

    result = await tool.run(input_data)

    assert len(result.bins) == 5
    assert result.total_count == 100
    assert result.min_price == 50000000
    assert result.max_price == 200000000


@pytest.mark.asyncio
async def test_get_price_distribution_percentiles(tool, mock_http_client):
    """Test that percentiles are correctly returned."""
    mock_summary = create_mock_summary(
        percentile_25=70000000,
        percentile_75=130000000,
    )
    tool._summarize_tool.run = AsyncMock(return_value=mock_summary)

    input_data = GetPriceDistributionInput(
        fromYear=2020,
        toYear=2021,
        area="13103",
    )

    result = await tool.run(input_data)

    assert result.percentile_25 == 70000000
    assert result.percentile_75 == 130000000


@pytest.mark.asyncio
async def test_get_price_distribution_custom_bins(tool, mock_http_client):
    """Test custom number of bins."""
    mock_summary = create_mock_summary()
    tool._summarize_tool.run = AsyncMock(return_value=mock_summary)

    input_data = GetPriceDistributionInput(
        fromYear=2020,
        toYear=2021,
        area="13103",
        numBins=10,
    )

    result = await tool.run(input_data)

    assert len(result.bins) == 10


@pytest.mark.asyncio
async def test_get_price_distribution_empty(tool, mock_http_client):
    """Test handling of empty dataset."""
    mock_summary = SummarizeTransactionsResponse(
        recordCount=0,
        priceByYear={},
        countByYear={},
        typeDistribution={},
        meta={"cacheHit": False, "dataset": "XIT001", "source": "test"},
    )
    tool._summarize_tool.run = AsyncMock(return_value=mock_summary)

    input_data = GetPriceDistributionInput(
        fromYear=2020,
        toYear=2021,
        area="13103",
    )

    result = await tool.run(input_data)

    assert result.total_count == 0
    assert len(result.bins) == 0
