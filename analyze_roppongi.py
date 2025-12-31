import json
import statistics
from pathlib import Path


def get_tsubo_price(price, area_m2):
    if not area_m2 or area_m2 <= 0:
        return 0
    tsubo = area_m2 * 0.3025
    return price / tsubo


def analyze():
    with open("roppongi_data.json", "r") as f:
        data = json.load(f)

    # 2. Extract Data from Transactions
    print("\n--- Market Data & Urban Planning (from Transactions) ---")
    tx = data.get("transactions", {}).get("geojson", {})
    tx_features = tx.get("features", [])

    roppongi_tx = []

    urban_planning_samples = {}  # (Zoning, FAR, BCR) -> count

    for f in tx_features:
        props = f.get("properties", {})
        # Filter for Roppongi
        # Check district_name_ja or address match
        dist = props.get("district_name_ja", "")
        addr = str(props)
        if "六本木" in dist or "六本木" in addr:
            roppongi_tx.append(props)

            # Extract Urban Planning Info
            zoning = props.get("land_use_name_ja")
            far = props.get("u_floor_area_ratio_ja")
            bcr = props.get("u_building_coverage_ratio_ja")
            if zoning and far and bcr:
                key = (zoning, far, bcr)
                urban_planning_samples[key] = urban_planning_samples.get(key, 0) + 1

    print(f"Total Transactions in Roppongi: {len(roppongi_tx)}")

    # Analyze Prices
    condos = []
    lands = []

    for props in roppongi_tx:
        price_str = props.get("u_transaction_price_total_ja", "")  # e.g. "300,000万円"
        if not price_str:
            continue

        # Parse price
        try:
            price_val = float(price_str.replace("万円", "").replace(",", "")) * 10000
        except:
            continue

        area_str = props.get("u_area_ja", "")  # "180㎡"
        try:
            area_val = float(
                area_str.replace("㎡", "").replace("m^2", "").replace(",", "")
            )
        except:
            area_val = 0

        type_ = props.get("land_type_name_ja")  # "中古マンション等" or "宅地（土地）"

        unit_price_tsubo = 0
        if area_val > 0:
            unit_price_tsubo = price_val / (area_val * 0.3025)

        item = {
            "price": price_val,
            "area": area_val,
            "tsubo_price": unit_price_tsubo,
            "year": props.get("u_construction_year_ja", ""),
            "trade_period": props.get("point_in_time_name_ja", ""),
        }

        if "マンション" in str(type_):
            condos.append(item)
        elif "宅地" in str(type_) and "土地" in str(type_):
            lands.append(item)

    # Report Urban Planning
    print("\n[Urban Planning Info from Transactions]")
    for (z, f, b), count in urban_planning_samples.items():
        print(f"  Zone: {z}, FAR: {f}, BCR: {b} (Count: {count})")

    # Report Land
    print("\n[Land Transactions]")
    if lands:
        tsubos = [x["tsubo_price"] for x in lands if x["tsubo_price"] > 0]
        if tsubos:
            avg = statistics.mean(tsubos)
            print(f"  Count: {len(lands)}")
            print(f"  Average Unit Price: {avg:,.0f} JPY/tsubo")
            print(f"  Min: {min(tsubos):,.0f}, Max: {max(tsubos):,.0f}")
    else:
        print("  No Land Transactions found.")

    # Report Condos
    print("\n[Condo Transactions]")
    if condos:
        c_tsubos = [x["tsubo_price"] for x in condos if x["tsubo_price"] > 0]
        c_prices = [x["price"] for x in condos]
        if c_tsubos:
            avg_t = statistics.mean(c_tsubos)
            avg_p = statistics.mean(c_prices)
            print(f"  Count: {len(condos)}")
            print(f"  Average Unit Price: {avg_t:,.0f} JPY/tsubo")
            print(f"  Average Total Price: {avg_p:,.0f} JPY")
            print(f"  Price Range: {min(c_prices):,.0f} - {max(c_prices):,.0f} JPY")
            print(
                f"  Unit Price Range: {min(c_tsubos):,.0f} - {max(c_tsubos):,.0f} JPY/tsubo"
            )


if __name__ == "__main__":
    analyze()
