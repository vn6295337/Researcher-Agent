#!/usr/bin/env python3
"""
Fetch raw volatility data from Yahoo Finance, Alpha Vantage, and FRED.
Outputs the data schema with actual values.
"""

import asyncio
import json
import sys
sys.path.insert(0, '/home/vn6295337/Researcher-Agent')

from mcp_client import call_mcp_server


async def fetch_volatility(ticker: str = 'AAPL'):
    """Fetch volatility from multiple sources."""
    result = await call_mcp_server(
        'volatility-basket',
        'get_all_sources_volatility',
        {'ticker': ticker},
        timeout=90
    )
    return result


def print_metric(key, val, indent=2):
    """Print a metric with proper indentation."""
    prefix = " " * indent
    print(f"\n{prefix}{key}")
    if isinstance(val, dict):
        for k, v in val.items():
            print(f"{prefix}  {k}: {v}")
    elif val is None:
        print(f"{prefix}  value: null")
    else:
        print(f"{prefix}  value: {val}")


def print_schema(data: dict, ticker: str):
    """Print data schema in plain text format."""
    print("Volatility Data Schema")
    print("=" * 50)
    print(f"\nExample Ticker: {ticker}")

    # Market volatility context
    if 'market_volatility_context' in data:
        ctx = data['market_volatility_context']
        print(f"\n\nMarket Volatility Context")
        print("-" * 40)
        print(f"description: {ctx.get('description')}")
        print(f"note: {ctx.get('note')}")
        for key in ['vix', 'vxn']:
            if key in ctx:
                print_metric(key, ctx[key])

    # Yahoo Finance
    if 'yahoo_finance' in data:
        yf = data['yahoo_finance']
        print(f"\n\nYahoo Finance (Primary)")
        print("-" * 40)
        print(f"source: {yf.get('source')}")
        print(f"as_of: {yf.get('as_of')}")
        for key, val in yf.get('data', {}).items():
            print_metric(key, val)

    # Alpha Vantage
    if 'alpha_vantage' in data:
        av = data['alpha_vantage']
        print(f"\n\nAlpha Vantage (Secondary)")
        print("-" * 40)
        print(f"source: {av.get('source')}")
        print(f"as_of: {av.get('as_of')}")
        for key, val in av.get('data', {}).items():
            print_metric(key, val)

    # Source hierarchy
    if 'primary_source_hierarchy' in data:
        print(f"\n\nPrimary Source Hierarchy")
        print("-" * 40)
        for key, val in data['primary_source_hierarchy'].items():
            print(f"{key}: {val}")


async def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'

    print(f"Fetching volatility for {ticker}...")
    data = await fetch_volatility(ticker)

    if data:
        print_schema(data, ticker)

        with open(f'/home/vn6295337/Researcher-Agent/docs/{ticker}_volatility_raw.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nRaw JSON saved to: docs/{ticker}_volatility_raw.json")
    else:
        print("Failed to fetch data")


if __name__ == '__main__':
    asyncio.run(main())
