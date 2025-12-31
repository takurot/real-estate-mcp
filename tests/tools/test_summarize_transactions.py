import pytest
from unittest.mock import AsyncMock, MagicMock
from mlit_mcp.tools.summarize_transactions import (
    SummarizeTransactionsTool,
    SummarizeTransactionsInput,
)
from mlit_mcp.http_client import FetchResult


@pytest.fixture
def mock_http_client():
    client = MagicMock()
    client.fetch = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_summarize_transactions_basic(mock_http_client):
    """Test basic aggregation of transaction data."""
    mock_data_2020 = [
        {
            "TradePrice": "100000000",
            "Type": "中古マンション等",
            "Period": "2020年第1四半期",
        },
        {
            "TradePrice": "200000000",
            "Type": "中古マンション等",
            "Period": "2020年第2四半期",
        },
    ]
    mock_data_2021 = [
        {"TradePrice": "150000000", "Type": "宅地(土地)", "Period": "2021年第1四半期"},
    ]
    mock_http_client.fetch.side_effect = [
        FetchResult(data={"data": mock_data_2020}, from_cache=False),
        FetchResult(data={"data": mock_data_2021}, from_cache=False),
    ]

    tool = SummarizeTransactionsTool(mock_http_client)
    input_data = SummarizeTransactionsInput(
        from_year=2020,
        to_year=2021,
        area="13103",
    )

    result = await tool.run(input_data)

    assert result.record_count == 3
    assert result.average_price == 150000000
    assert result.min_price == 100000000
    assert result.max_price == 200000000
    assert "中古マンション等" in result.type_distribution
    assert result.type_distribution["中古マンション等"] == 2
    assert result.type_distribution["宅地(土地)"] == 1


@pytest.mark.asyncio
async def test_summarize_transactions_empty(mock_http_client):
    """Test handling of empty dataset."""
    mock_http_client.fetch.return_value = FetchResult(
        data={"data": []}, from_cache=False
    )

    tool = SummarizeTransactionsTool(mock_http_client)
    input_data = SummarizeTransactionsInput(
        from_year=2020,
        to_year=2020,
        area="13103",
    )

    result = await tool.run(input_data)

    assert result.record_count == 0
    assert result.average_price is None
    assert result.median_price is None


@pytest.mark.asyncio
async def test_summarize_transactions_price_by_year(mock_http_client):
    """Test price aggregation by year."""
    mock_data = [
        {
            "TradePrice": "100000000",
            "Type": "中古マンション等",
            "Period": "2020年第1四半期",
        },
        {
            "TradePrice": "120000000",
            "Type": "中古マンション等",
            "Period": "2020年第2四半期",
        },
        {
            "TradePrice": "200000000",
            "Type": "中古マンション等",
            "Period": "2021年第1四半期",
        },
    ]
    mock_http_client.fetch.return_value = FetchResult(
        data={"data": mock_data}, from_cache=False
    )

    tool = SummarizeTransactionsTool(mock_http_client)
    input_data = SummarizeTransactionsInput(
        from_year=2020,
        to_year=2021,
        area="13103",
    )

    result = await tool.run(input_data)

    assert "2020" in result.price_by_year
    assert "2021" in result.price_by_year
    assert result.price_by_year["2020"] == 110000000  # (100M + 120M) / 2
    assert result.price_by_year["2021"] == 200000000
