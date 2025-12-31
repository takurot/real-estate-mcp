import asyncio
import json
import logging
from pathlib import Path
import tempfile
import sys
import os

# Add project root to path
sys.path.append("/Users/takurot/src/real-estate")

from mlit_mcp.cache import BinaryFileCache, InMemoryTTLCache
from mlit_mcp.http_client import MLITHttpClient
from mlit_mcp.settings import get_settings
from mlit_mcp.tools.fetch_urban_planning_zones import (
    FetchUrbanPlanningZonesTool,
    FetchUrbanPlanningZonesInput,
)
from mlit_mcp.tools.fetch_land_price_points import (
    FetchLandPricePointsTool,
    FetchLandPricePointsInput,
)
from mlit_mcp.tools.fetch_transaction_points import (
    FetchTransactionPointsTool,
    FetchTransactionPointsInput,
)

# Setup logging
logging.basicConfig(level=logging.INFO)


async def main():
    settings = get_settings()
    # Cache config matching mcp_server.py
    cache_root = Path(tempfile.gettempdir()) / "mlit_mcp_cache"
    json_cache = InMemoryTTLCache(maxsize=256, ttl=6 * 60 * 60)
    file_cache = BinaryFileCache(cache_root / "files", ttl_seconds=6 * 60 * 60)

    client = MLITHttpClient(
        base_url=str(settings.base_url),
        json_cache=json_cache,
        file_cache=file_cache,
        api_key=settings.api_key or os.getenv("MLIT_API_KEY"),
    )

    # Coordinates for Roppongi 3-chome (Z14)
    Z, X, Y = 14, 14551, 6452

    results = {}

    print("Fetching Urban Planning Zones...")
    urban_tool = FetchUrbanPlanningZonesTool(client)
    urban_res = await urban_tool.run(FetchUrbanPlanningZonesInput(z=Z, x=X, y=Y))
    results["urban_planning"] = urban_res.model_dump(by_alias=True, exclude_none=True)

    print("Fetching Land Price Points (2024)...")
    land_tool = FetchLandPricePointsTool(client)
    land_res = await land_tool.run(FetchLandPricePointsInput(z=Z, x=X, y=Y, year=2024))
    results["land_prices"] = land_res.model_dump(by_alias=True, exclude_none=True)

    print("Fetching Transaction Points (2024 Q3 - 2025 Q3)...")
    tx_tool = FetchTransactionPointsTool(client)
    tx_res = await tx_tool.run(
        FetchTransactionPointsInput(
            z=Z, x=X, y=Y, from_quarter="20243", to_quarter="20253"
        )
    )
    results["transactions"] = tx_res.model_dump(by_alias=True, exclude_none=True)

    # Save results to a file
    out_path = Path("roppongi_data.json")
    with open(out_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Done. Saved to {out_path.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
