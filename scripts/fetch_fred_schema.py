#!/usr/bin/env python3
"""
Fetch raw FRED data and output the schema.
Shows both raw API response and enriched format.
"""

import asyncio
import json
import os
import sys
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

FRED_API_KEY = os.getenv("FRED_API_KEY") or os.getenv("FRED_VIX_API_KEY")
FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# Series to fetch
SERIES = {
    "gdp_growth": "A191RL1Q225SBEA",
    "interest_rate": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
    "vix": "VIXCLS",
    "vxn": "VXNCLS",
}


async def fetch_series_raw(series_id: str, limit: int = 5) -> dict:
    """Fetch raw FRED data for a series."""
    if not FRED_API_KEY:
        return {"error": "FRED_API_KEY not configured"}

    async with httpx.AsyncClient() as client:
        # Get series info
        info_url = f"{FRED_BASE_URL}/series"
        info_params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json"
        }
        info_resp = await client.get(info_url, params=info_params, timeout=10)
        info_data = info_resp.json()

        # Get observations
        obs_url = f"{FRED_BASE_URL}/series/observations"
        obs_params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit
        }
        obs_resp = await client.get(obs_url, params=obs_params, timeout=10)
        obs_data = obs_resp.json()

        return {
            "series_info": info_data,
            "observations": obs_data
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


async def main():
    print("FRED Data Schema")
    print("=" * 60)
    print()
    print("Endpoint: https://api.stlouisfed.org/fred/series/observations")
    print()

    if not FRED_API_KEY:
        print("ERROR: FRED_API_KEY not configured")
        print("Add FRED_API_KEY to ~/.env file")
        return

    all_data = {}

    # Fetch each series
    for name, series_id in SERIES.items():
        print(f"Fetching {name} ({series_id})...")
        data = await fetch_series_raw(series_id, limit=3)
        all_data[name] = data

    print()
    print("=" * 60)
    print()

    # Print raw API response structure
    print("Raw API Response Structure")
    print("-" * 40)
    print()

    # Series info fields
    sample = all_data.get("gdp_growth", {})
    series_info = sample.get("series_info", {}).get("seriess", [{}])[0]

    rows = [["field", "description", "example"]]
    rows.append(["id", "Series identifier", series_info.get("id", "")])
    rows.append(["title", "Series title", series_info.get("title", "")[:40]])
    rows.append(["units", "Data units", series_info.get("units", "")])
    rows.append(["frequency", "Update frequency", series_info.get("frequency", "")])
    rows.append(["seasonal_adjustment", "Adjustment type", series_info.get("seasonal_adjustment", "")])
    rows.append(["last_updated", "Last update time", series_info.get("last_updated", "")])
    print_table("Series Info (seriess[0])", rows)

    # Observation fields
    obs = sample.get("observations", {}).get("observations", [{}])[0]
    rows = [["field", "description", "example"]]
    rows.append(["realtime_start", "Real-time period start", obs.get("realtime_start", "")])
    rows.append(["realtime_end", "Real-time period end", obs.get("realtime_end", "")])
    rows.append(["date", "Observation date", obs.get("date", "")])
    rows.append(["value", "Data value", obs.get("value", "")])
    print_table("Observation (observations[])", rows)

    print()
    print()
    print("Series Data")
    print("-" * 40)

    # Print each series
    for name, data in all_data.items():
        series_info = data.get("series_info", {}).get("seriess", [{}])[0]
        observations = data.get("observations", {}).get("observations", [])

        # Get latest observation
        latest = None
        for obs in observations:
            if obs.get("value") and obs["value"] != ".":
                latest = obs
                break

        rows = [["field", "value"]]
        rows.append(["series_id", SERIES[name]])
        rows.append(["title", series_info.get("title", "")[:50]])
        rows.append(["units", series_info.get("units", "")])
        rows.append(["frequency", series_info.get("frequency", "")])
        rows.append(["date", latest.get("date", "") if latest else ""])
        rows.append(["value", latest.get("value", "") if latest else ""])
        rows.append(["last_updated", series_info.get("last_updated", "")[:19]])

        print_table(name, rows)

    # Save raw JSON
    output_path = Path(__file__).parent.parent / "docs" / "fred_raw.json"
    with open(output_path, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"\nRaw JSON saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
