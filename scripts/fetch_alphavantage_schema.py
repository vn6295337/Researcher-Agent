#!/usr/bin/env python3
"""
Fetch raw Alpha Vantage data and output the schema.
Shows raw API response structure and field descriptions.
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

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")


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


async def fetch_overview(ticker: str) -> dict:
    """Fetch company overview from Alpha Vantage."""
    if not ALPHA_VANTAGE_KEY:
        return {"error": "ALPHA_VANTAGE_API_KEY not configured"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": "OVERVIEW",
                "symbol": ticker,
                "apikey": ALPHA_VANTAGE_KEY
            }
            response = await client.get(url, params=params, timeout=15)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


async def main():
    print("Alpha Vantage Data Schema")
    print("=" * 60)
    print()
    print("Endpoint: https://www.alphavantage.co/query?function=OVERVIEW")
    print()

    if not ALPHA_VANTAGE_KEY:
        print("ERROR: ALPHA_VANTAGE_API_KEY not configured")
        print("Add ALPHA_VANTAGE_API_KEY to ~/.env file")
        print("Get free key at: https://www.alphavantage.co/support/#api-key")
        return

    print("Fetching AAPL overview...")
    data = await fetch_overview("AAPL")

    if "error" in data or "Error Message" in data:
        print(f"ERROR: {data}")
        return

    print()
    print("=" * 60)
    print()

    # Print raw API response structure
    print("Raw API Response Structure")
    print("-" * 40)

    # Company Info
    rows = [["field", "value"]]
    rows.append(["Symbol", data.get("Symbol", "")])
    rows.append(["Name", data.get("Name", "")])
    rows.append(["Exchange", data.get("Exchange", "")])
    rows.append(["Currency", data.get("Currency", "")])
    rows.append(["Country", data.get("Country", "")])
    rows.append(["Sector", data.get("Sector", "")])
    rows.append(["Industry", data.get("Industry", "")])
    print_table("Company Info", rows)

    # Valuation Metrics
    rows = [["field", "value"]]
    rows.append(["MarketCapitalization", data.get("MarketCapitalization", "")])
    rows.append(["TrailingPE", data.get("TrailingPE", "")])
    rows.append(["ForwardPE", data.get("ForwardPE", "")])
    rows.append(["PEGRatio", data.get("PEGRatio", "")])
    rows.append(["PriceToBookRatio", data.get("PriceToBookRatio", "")])
    rows.append(["PriceToSalesRatioTTM", data.get("PriceToSalesRatioTTM", "")])
    rows.append(["EVToEBITDA", data.get("EVToEBITDA", "")])
    rows.append(["EVToRevenue", data.get("EVToRevenue", "")])
    print_table("Valuation Metrics", rows)

    # Growth Metrics
    rows = [["field", "value"]]
    rows.append(["QuarterlyEarningsGrowthYOY", data.get("QuarterlyEarningsGrowthYOY", "")])
    rows.append(["QuarterlyRevenueGrowthYOY", data.get("QuarterlyRevenueGrowthYOY", "")])
    rows.append(["AnalystTargetPrice", data.get("AnalystTargetPrice", "")])
    print_table("Growth Metrics", rows)

    # Financial Metrics
    rows = [["field", "value"]]
    rows.append(["EBITDA", data.get("EBITDA", "")])
    rows.append(["RevenueTTM", data.get("RevenueTTM", "")])
    rows.append(["GrossProfitTTM", data.get("GrossProfitTTM", "")])
    rows.append(["DilutedEPSTTM", data.get("DilutedEPSTTM", "")])
    rows.append(["ProfitMargin", data.get("ProfitMargin", "")])
    rows.append(["OperatingMarginTTM", data.get("OperatingMarginTTM", "")])
    rows.append(["ReturnOnAssetsTTM", data.get("ReturnOnAssetsTTM", "")])
    rows.append(["ReturnOnEquityTTM", data.get("ReturnOnEquityTTM", "")])
    print_table("Financial Metrics", rows)

    # Dividend & Book Value
    rows = [["field", "value"]]
    rows.append(["DividendPerShare", data.get("DividendPerShare", "")])
    rows.append(["DividendYield", data.get("DividendYield", "")])
    rows.append(["ExDividendDate", data.get("ExDividendDate", "")])
    rows.append(["BookValue", data.get("BookValue", "")])
    print_table("Dividend & Book Value", rows)

    # Moving Averages
    rows = [["field", "value"]]
    rows.append(["50DayMovingAverage", data.get("50DayMovingAverage", "")])
    rows.append(["200DayMovingAverage", data.get("200DayMovingAverage", "")])
    rows.append(["52WeekHigh", data.get("52WeekHigh", "")])
    rows.append(["52WeekLow", data.get("52WeekLow", "")])
    rows.append(["Beta", data.get("Beta", "")])
    print_table("Moving Averages & Risk", rows)

    # Save raw JSON
    output_path = Path(__file__).parent.parent / "docs" / "alphavantage_raw.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nRaw JSON saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
