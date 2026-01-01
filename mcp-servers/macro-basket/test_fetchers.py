#!/usr/bin/env python3
"""
Test script for Macro Basket fetchers.

Usage:
    python test_fetchers.py
    python test_fetchers.py gdp
    python test_fetchers.py rates
    python test_fetchers.py cpi
    python test_fetchers.py unemployment
    python test_fetchers.py all
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    fetch_gdp_growth,
    fetch_interest_rates,
    fetch_cpi,
    fetch_unemployment,
    get_full_macro_basket,
    FRED_API_KEY
)


async def test_gdp():
    """Test GDP growth fetcher."""
    print("\n" + "="*60)
    print("GDP GROWTH")
    print("="*60)
    result = await fetch_gdp_growth()
    print(json.dumps(result, indent=2))
    return result


async def test_interest_rates():
    """Test interest rate fetcher."""
    print("\n" + "="*60)
    print("INTEREST RATES (Federal Funds Rate)")
    print("="*60)
    result = await fetch_interest_rates()
    print(json.dumps(result, indent=2))
    return result


async def test_cpi():
    """Test CPI/inflation fetcher."""
    print("\n" + "="*60)
    print("CPI / INFLATION")
    print("="*60)
    result = await fetch_cpi()
    print(json.dumps(result, indent=2))
    return result


async def test_unemployment():
    """Test unemployment fetcher."""
    print("\n" + "="*60)
    print("UNEMPLOYMENT RATE")
    print("="*60)
    result = await fetch_unemployment()
    print(json.dumps(result, indent=2))
    return result


async def test_full_basket():
    """Test full macro basket."""
    print("\n" + "="*60)
    print("FULL MACRO BASKET")
    print("="*60)
    result = await get_full_macro_basket()
    print(json.dumps(result, indent=2))
    return result


async def main():
    # Check API key
    if not FRED_API_KEY:
        print("WARNING: FRED_API_KEY not set. Get free key at:")
        print("https://fred.stlouisfed.org/docs/api/api_key.html")
        print()

    # Parse arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "gdp":
            await test_gdp()
        elif arg == "rates":
            await test_interest_rates()
        elif arg == "cpi":
            await test_cpi()
        elif arg == "unemployment":
            await test_unemployment()
        elif arg == "all":
            await test_full_basket()
        else:
            print(f"Unknown argument: {arg}")
            print("Usage: python test_fetchers.py [gdp|rates|cpi|unemployment|all]")
    else:
        # Run all tests
        await test_gdp()
        await test_interest_rates()
        await test_cpi()
        await test_unemployment()
        print("\n" + "="*60)
        print("FULL BASKET SUMMARY")
        print("="*60)
        await test_full_basket()


if __name__ == "__main__":
    asyncio.run(main())
