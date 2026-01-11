#!/usr/bin/env python3
"""
Fetch raw BLS (Bureau of Labor Statistics) data and output the schema.
Shows raw API response structure for CPI and Unemployment data.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import httpx

# Load environment variables
env_paths = [
    Path.home() / ".env",
    Path(__file__).parent.parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

BLS_API_KEY = os.getenv("BLS_API_KEY")
BLS_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# BLS Series IDs
SERIES = {
    "cpi": "CUUR0000SA0",        # CPI-U All items
    "unemployment": "LNS14000000"  # Unemployment rate
}


def print_table(title: str, rows: list, col_widths: list = None):
    """Print ASCII table."""
    if not rows:
        return

    # Calculate column widths
    if col_widths is None:
        col_widths = []
        for col in range(len(rows[0])):
            width = max(len(str(row[col])) for row in rows)
            col_widths.append(width)

    # Print header
    print(f"\n{title}")

    # Top border
    line = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    print(line)

    # Header row
    header = rows[0]
    row_str = "│" + "│".join(f" {str(header[i]).ljust(col_widths[i])} " for i in range(len(header))) + "│"
    print(row_str)

    # Separator
    line = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    print(line)

    # Data rows
    for row in rows[1:]:
        row_str = "│" + "│".join(f" {str(row[i]).ljust(col_widths[i])} " for i in range(len(row))) + "│"
        print(row_str)

    # Bottom border
    line = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
    print(line)


async def fetch_bls_data(series_ids: list) -> dict:
    """Fetch data from BLS API."""
    current_year = datetime.now().year

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "seriesid": series_ids,
                "startyear": str(current_year - 2),
                "endyear": str(current_year)
            }

            # Add API key if available (for v2 with higher limits)
            if BLS_API_KEY:
                payload["registrationkey"] = BLS_API_KEY

            headers = {"Content-Type": "application/json"}
            response = await client.post(BLS_BASE_URL, json=payload, headers=headers, timeout=15)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


async def main():
    print("BLS Data Schema")
    print("=" * 60)
    print()
    print("Endpoint: https://api.bls.gov/publicAPI/v2/timeseries/data/")
    print("Method: POST with JSON payload")
    print()
    print("Series IDs:")
    print("  - CUUR0000SA0: CPI-U All items (Consumer Price Index)")
    print("  - LNS14000000: Unemployment Rate")
    print()

    print("Fetching CPI and Unemployment data...")
    data = await fetch_bls_data(list(SERIES.values()))

    if "error" in data:
        print(f"ERROR: {data}")
        return

    if data.get("status") != "REQUEST_SUCCEEDED":
        print(f"ERROR: {data.get('message', 'Unknown error')}")
        return

    print()
    print("=" * 60)
    print()

    # Print raw API response structure
    print("Raw API Response Structure")
    print("-" * 40)

    # Request payload
    rows = [["field", "description"]]
    rows.append(["seriesid[]", "Array of BLS series IDs to fetch"])
    rows.append(["startyear", "Start year for data range"])
    rows.append(["endyear", "End year for data range"])
    rows.append(["registrationkey", "Optional API key for higher limits"])
    print_table("Request Payload", rows)

    # Response metadata
    rows = [["field", "value"]]
    rows.append(["status", data.get("status", "")])
    rows.append(["responseTime", str(data.get("responseTime", ""))])
    rows.append(["message[]", "Array of status messages"])
    print_table("Response Metadata", rows)

    # Results structure
    results = data.get("Results", {})
    series_list = results.get("series", [])

    rows = [["field", "description"]]
    rows.append(["Results.series[]", f"Array of series data (count: {len(series_list)})"])
    print_table("Results Structure", rows)

    # Series data structure
    if series_list:
        sample_series = series_list[0]
        rows = [["field", "value"]]
        rows.append(["seriesID", sample_series.get("seriesID", "")])
        rows.append(["data[]", f"Array of observations (count: {len(sample_series.get('data', []))})"])
        print_table("series[0] (Series Structure)", rows)

        # Data observation structure
        data_obs = sample_series.get("data", [])
        if data_obs:
            sample_obs = data_obs[0]
            rows = [["field", "value"]]
            rows.append(["year", sample_obs.get("year", "")])
            rows.append(["period", sample_obs.get("period", "")])
            rows.append(["periodName", sample_obs.get("periodName", "")])
            rows.append(["value", sample_obs.get("value", "")])
            rows.append(["footnotes[]", str(sample_obs.get("footnotes", []))])
            print_table("data[0] (Observation Structure)", rows)

    # Field descriptions
    print()
    print()
    print("Field Descriptions")
    print("-" * 40)

    rows = [["field", "description"]]
    rows.append(["seriesID", "BLS series identifier"])
    rows.append(["year", "4-digit year (e.g., 2025)"])
    rows.append(["period", "Period code (M01-M12 for monthly, A01 for annual)"])
    rows.append(["periodName", "Human-readable period (January, February, etc.)"])
    rows.append(["value", "Data value as string"])
    rows.append(["footnotes", "Array of footnote codes"])
    print_table("Field Descriptions", rows)

    # Series data
    print()
    print()
    print("Series Data")
    print("-" * 40)

    for series in series_list:
        series_id = series.get("seriesID", "")
        series_name = "CPI-U All Items" if series_id == "CUUR0000SA0" else "Unemployment Rate"
        data_obs = series.get("data", [])

        rows = [["field", "value"]]
        rows.append(["series_id", series_id])
        rows.append(["name", series_name])

        if data_obs:
            latest = data_obs[0]
            rows.append(["period", f"{latest.get('year')}-{latest.get('periodName', latest.get('period'))}"])
            rows.append(["value", latest.get("value", "")])
        print_table(series_name, rows)

    # Save raw JSON
    output_path = Path(__file__).parent.parent / "docs" / "bls_raw.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nRaw JSON saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
