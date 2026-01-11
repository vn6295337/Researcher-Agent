#!/usr/bin/env python3
"""
Fetch raw Yahoo Finance Options data and output the schema.
Shows raw API response structure for options chain data.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
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


async def fetch_options(ticker: str) -> dict:
    """Fetch options chain from Yahoo Finance."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://query1.finance.yahoo.com/v7/finance/options/{ticker}"
            response = await client.get(url, headers=YAHOO_HEADERS, timeout=15)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


async def main():
    print("Yahoo Finance Options Data Schema")
    print("=" * 60)
    print()
    print("Endpoint: https://query1.finance.yahoo.com/v7/finance/options/{ticker}")
    print()

    print("Fetching AAPL options chain...")
    data = await fetch_options("AAPL")

    if "error" in data:
        print(f"ERROR: {data}")
        return

    option_chain = data.get("optionChain", {})
    result = option_chain.get("result", [{}])[0] if option_chain.get("result") else {}

    if not result:
        print("ERROR: No options data returned")
        return

    print()
    print("=" * 60)
    print()

    # Print raw API response structure
    print("Raw API Response Structure")
    print("-" * 40)

    # Underlying quote
    quote = result.get("quote", {})
    rows = [["field", "value"]]
    rows.append(["symbol", quote.get("symbol", "")])
    rows.append(["regularMarketPrice", quote.get("regularMarketPrice", "")])
    rows.append(["regularMarketTime", quote.get("regularMarketTime", "")])
    rows.append(["regularMarketChange", quote.get("regularMarketChange", "")])
    rows.append(["regularMarketChangePercent", quote.get("regularMarketChangePercent", "")])
    print_table("quote (Underlying)", rows)

    # Expiration dates
    expirations = result.get("expirationDates", [])
    rows = [["field", "description"]]
    rows.append(["expirationDates[]", "Unix timestamps of available expiration dates"])
    rows.append(["count", str(len(expirations))])
    if expirations:
        rows.append(["first", str(expirations[0])])
        rows.append(["last", str(expirations[-1])])
    print_table("Expiration Dates", rows)

    # Strikes
    strikes = result.get("strikes", [])
    rows = [["field", "description"]]
    rows.append(["strikes[]", "Available strike prices"])
    rows.append(["count", str(len(strikes))])
    if strikes:
        rows.append(["min", str(min(strikes))])
        rows.append(["max", str(max(strikes))])
    print_table("Strike Prices", rows)

    # Options data structure
    options = result.get("options", [{}])[0] if result.get("options") else {}
    calls = options.get("calls", [])
    puts = options.get("puts", [])

    rows = [["field", "description"]]
    rows.append(["expirationDate", "Expiration date (Unix timestamp)"])
    rows.append(["calls[]", f"Call options array (count: {len(calls)})"])
    rows.append(["puts[]", f"Put options array (count: {len(puts)})"])
    print_table("options[0] (First Expiration)", rows)

    # Call/Put contract fields
    if calls:
        sample_call = calls[0]
        rows = [["field", "value"]]
        rows.append(["contractSymbol", sample_call.get("contractSymbol", "")])
        rows.append(["strike", sample_call.get("strike", "")])
        rows.append(["currency", sample_call.get("currency", "")])
        rows.append(["lastPrice", sample_call.get("lastPrice", "")])
        rows.append(["change", sample_call.get("change", "")])
        rows.append(["percentChange", sample_call.get("percentChange", "")])
        rows.append(["volume", sample_call.get("volume", "")])
        rows.append(["openInterest", sample_call.get("openInterest", "")])
        rows.append(["bid", sample_call.get("bid", "")])
        rows.append(["ask", sample_call.get("ask", "")])
        rows.append(["impliedVolatility", sample_call.get("impliedVolatility", "")])
        rows.append(["inTheMoney", sample_call.get("inTheMoney", "")])
        rows.append(["expiration", sample_call.get("expiration", "")])
        rows.append(["lastTradeDate", sample_call.get("lastTradeDate", "")])
        print_table("calls[0] / puts[0] (Contract Fields)", rows)

    # ATM implied volatility example
    print()
    print()
    print("Implied Volatility Extraction")
    print("-" * 40)

    current_price = quote.get("regularMarketPrice", 0)
    if calls and current_price:
        atm_call = min(calls, key=lambda x: abs(x.get("strike", 0) - current_price))
        iv = atm_call.get("impliedVolatility", 0) * 100

        rows = [["field", "value"]]
        rows.append(["currentPrice", f"{current_price:.2f}"])
        rows.append(["atmStrike", atm_call.get("strike", "")])
        rows.append(["impliedVolatility (raw)", atm_call.get("impliedVolatility", "")])
        rows.append(["impliedVolatility (%)", f"{iv:.2f}%"])
        print_table("ATM Call Option", rows)

    # Save raw JSON
    output_path = Path(__file__).parent.parent / "docs" / "yahoo_options_raw.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nRaw JSON saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
