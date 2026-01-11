#!/usr/bin/env python3
"""
Fetch raw financials data from SEC EDGAR and Yahoo Finance.
Outputs the data schema with actual values.
"""

import asyncio
import json
import sys
sys.path.insert(0, '/home/vn6295337/Researcher-Agent')

from mcp_client import call_mcp_server


async def fetch_financials(ticker: str = 'AAPL'):
    """Fetch financials from SEC EDGAR and Yahoo Finance."""
    result = await call_mcp_server(
        'fundamentals-basket',
        'get_all_sources_fundamentals',
        {'ticker': ticker},
        timeout=90
    )
    return result


def print_schema(data: dict, ticker: str):
    """Print data schema in plain text format."""
    print("SEC EDGAR & Yahoo Finance Data Schema")
    print("=" * 40)
    print(f"\nExample Ticker: {ticker}")
    print()

    # SEC EDGAR
    if 'sec_edgar' in data:
        sec = data['sec_edgar']
        print("\nSEC EDGAR")
        print("-" * 40)
        print(f"source: {sec.get('source')}")
        print(f"as_of: {sec.get('as_of')}")

        sec_data = sec.get('data', {})
        for category in ['financials', 'debt', 'cash_flow']:
            if category in sec_data:
                print(f"\n{category.upper()}")
                cat_data = sec_data[category]
                for key, val in cat_data.items():
                    if key in ['ticker', 'source', 'as_of']:
                        continue
                    print(f"\n  {key}")
                    if isinstance(val, dict):
                        for k, v in val.items():
                            print(f"    {k}: {v}")
                    else:
                        print(f"    value: {val}")

    # Yahoo Finance
    if 'yahoo_finance' in data:
        yf = data['yahoo_finance']
        print("\n\nYahoo Finance")
        print("-" * 40)
        print(f"source: {yf.get('source')}")
        print(f"as_of: {yf.get('as_of')}")

        yf_data = yf.get('data', {})
        for category in ['financials', 'debt', 'cash_flow']:
            if category in yf_data:
                print(f"\n{category.upper()}")
                cat_data = yf_data[category]
                for key, val in cat_data.items():
                    if key in ['ticker', 'source', 'as_of']:
                        continue
                    print(f"\n  {key}")
                    if isinstance(val, dict):
                        for k, v in val.items():
                            print(f"    {k}: {v}")
                    else:
                        print(f"    value: {val}")


async def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'

    print(f"Fetching financials for {ticker}...")
    data = await fetch_financials(ticker)

    if data:
        print_schema(data, ticker)

        # Also save raw JSON
        with open(f'/home/vn6295337/Researcher-Agent/docs/{ticker}_financials_raw.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nRaw JSON saved to: docs/{ticker}_financials_raw.json")
    else:
        print("Failed to fetch data")


if __name__ == '__main__':
    asyncio.run(main())
