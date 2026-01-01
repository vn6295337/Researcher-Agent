#!/usr/bin/env python3
"""
Test script for Valuation Basket fetchers.

Usage:
    python test_fetchers.py AAPL
    python test_fetchers.py AAPL pe
    python test_fetchers.py AAPL ps
    python test_fetchers.py AAPL pb
    python test_fetchers.py AAPL ev
    python test_fetchers.py AAPL peg
    python test_fetchers.py AAPL all
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    fetch_pe_ratio,
    fetch_ps_ratio,
    fetch_pb_ratio,
    fetch_ev_ebitda,
    fetch_peg_ratio,
    get_full_valuation_basket
)


async def test_pe(ticker: str):
    """Test P/E ratio fetcher."""
    print("\n" + "="*60)
    print(f"P/E RATIO - {ticker}")
    print("="*60)
    result = await fetch_pe_ratio(ticker)
    print(json.dumps(result, indent=2))
    return result


async def test_ps(ticker: str):
    """Test P/S ratio fetcher."""
    print("\n" + "="*60)
    print(f"P/S RATIO - {ticker}")
    print("="*60)
    result = await fetch_ps_ratio(ticker)
    print(json.dumps(result, indent=2))
    return result


async def test_pb(ticker: str):
    """Test P/B ratio fetcher."""
    print("\n" + "="*60)
    print(f"P/B RATIO - {ticker}")
    print("="*60)
    result = await fetch_pb_ratio(ticker)
    print(json.dumps(result, indent=2))
    return result


async def test_ev_ebitda(ticker: str):
    """Test EV/EBITDA fetcher."""
    print("\n" + "="*60)
    print(f"EV/EBITDA - {ticker}")
    print("="*60)
    result = await fetch_ev_ebitda(ticker)
    print(json.dumps(result, indent=2))
    return result


async def test_peg(ticker: str):
    """Test PEG ratio fetcher."""
    print("\n" + "="*60)
    print(f"PEG RATIO - {ticker}")
    print("="*60)
    result = await fetch_peg_ratio(ticker)
    print(json.dumps(result, indent=2))
    return result


async def test_full_basket(ticker: str):
    """Test full valuation basket."""
    print("\n" + "="*60)
    print(f"FULL VALUATION BASKET - {ticker}")
    print("="*60)
    result = await get_full_valuation_basket(ticker)
    print(json.dumps(result, indent=2))
    return result


async def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python test_fetchers.py TICKER [pe|ps|pb|ev|peg|all]")
        print("Example: python test_fetchers.py AAPL")
        print("         python test_fetchers.py TSLA pe")
        return

    ticker = sys.argv[1].upper()
    metric = sys.argv[2].lower() if len(sys.argv) > 2 else None

    print(f"\nTesting valuation metrics for: {ticker}")

    if metric == "pe":
        await test_pe(ticker)
    elif metric == "ps":
        await test_ps(ticker)
    elif metric == "pb":
        await test_pb(ticker)
    elif metric == "ev":
        await test_ev_ebitda(ticker)
    elif metric == "peg":
        await test_peg(ticker)
    elif metric == "all":
        await test_full_basket(ticker)
    else:
        # Run all tests
        await test_pe(ticker)
        await test_ps(ticker)
        await test_pb(ticker)
        await test_ev_ebitda(ticker)
        await test_peg(ticker)
        print("\n" + "="*60)
        print("FULL BASKET SUMMARY")
        print("="*60)
        await test_full_basket(ticker)


if __name__ == "__main__":
    asyncio.run(main())
