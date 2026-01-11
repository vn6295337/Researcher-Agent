#!/usr/bin/env python3
"""
Fetch raw valuation data from Yahoo Finance and Alpha Vantage.
Outputs the data schema with actual values.
"""

import asyncio
import json
import sys
sys.path.insert(0, '/home/vn6295337/Researcher-Agent')

from mcp_client import call_mcp_server


async def fetch_valuation(ticker: str = 'AAPL'):
    """Fetch valuation from Yahoo Finance and Alpha Vantage."""
    result = await call_mcp_server(
        'valuation-basket',
        'get_all_sources_valuation',
        {'ticker': ticker},
        timeout=90
    )
    return result


def print_schema(data: dict, ticker: str):
    """Print data schema in plain text format."""
    print("Yahoo Finance & Alpha Vantage Valuation Data Schema")
    print("=" * 50)
    print(f"\nExample Ticker: {ticker}")
    print()

    for source_key in ['yahoo_finance', 'alpha_vantage']:
        if source_key in data:
            source_data = data[source_key]
            source_name = source_data.get('source', source_key)

            print(f"\n{source_name}")
            print("-" * 40)
            print(f"source: {source_name}")
            print(f"as_of: {source_data.get('as_of')}")

            metrics = source_data.get('data', {})
            for key, val in metrics.items():
                print(f"\n  {key}")
                if isinstance(val, dict):
                    for k, v in val.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"    value: {val}")


async def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'

    print(f"Fetching valuation for {ticker}...")
    data = await fetch_valuation(ticker)

    if data:
        print_schema(data, ticker)

        # Also save raw JSON
        with open(f'/home/vn6295337/Researcher-Agent/docs/{ticker}_valuation_raw.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nRaw JSON saved to: docs/{ticker}_valuation_raw.json")
    else:
        print("Failed to fetch data")


if __name__ == '__main__':
    asyncio.run(main())
