#!/usr/bin/env python3
"""
Test script for volatility fetchers (standalone, no MCP required).
Usage: python test_fetchers.py TSLA
"""

import asyncio
import sys
import os
from pathlib import Path

# Load .env from home directory
from dotenv import load_dotenv
env_path = Path.home() / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from {env_path}")

# Import fetchers directly (bypass MCP)
sys.path.insert(0, '.')

async def test_all(ticker: str):
    """Test all fetchers for a given ticker."""
    import httpx
    import statistics
    from datetime import datetime

    # Yahoo requires these headers to avoid 401/403
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    print(f"\n{'='*60}")
    print(f"Testing Volatility Basket for: {ticker}")
    print(f"{'='*60}\n")

    # Check for API keys
    fred_key = os.getenv("FRED_API_KEY") or os.getenv("FRED_VIX_API_KEY")
    print(f"FRED API Key: {'Found' if fred_key else 'Not found'}")
    print()

    # 1. VIX - Try FRED first, then Yahoo
    print("1. Fetching VIX...")
    vix_source = None

    # Try FRED first (authoritative)
    if fred_key:
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": "VIXCLS",
                    "api_key": fred_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 5
                }
                response = await client.get(url, params=params, timeout=10)
                data = response.json()
                observations = data.get("observations", [])
                for obs in observations:
                    if obs.get("value") and obs["value"] != ".":
                        vix = float(obs["value"])
                        vix_source = "FRED"
                        print(f"   VIX: {vix:.2f} (Source: FRED - {obs.get('date')})")
                        break
        except Exception as e:
            print(f"   FRED Error: {e}")

    # Fallback to Yahoo
    if not vix_source:
        try:
            async with httpx.AsyncClient() as client:
                url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
                response = await client.get(url, params={"interval": "1d", "range": "5d"}, headers=HEADERS, timeout=10)
                data = response.json()
                vix = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                print(f"   VIX: {vix:.2f} (Source: Yahoo Finance)")
        except Exception as e:
            print(f"   VIX Error: {e}")

    # 2. Beta (calculated from 1-year data vs S&P 500)
    print(f"\n2. Calculating Beta for {ticker} vs S&P 500...")
    try:
        async with httpx.AsyncClient() as client:
            stock_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            market_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
            params = {"interval": "1d", "range": "1y"}

            stock_resp = await client.get(stock_url, params=params, headers=HEADERS, timeout=10)
            market_resp = await client.get(market_url, params=params, headers=HEADERS, timeout=10)

            stock_closes = stock_resp.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            market_closes = market_resp.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]

            stock_closes = [c for c in stock_closes if c is not None]
            market_closes = [c for c in market_closes if c is not None]
            min_len = min(len(stock_closes), len(market_closes))
            stock_closes = stock_closes[-min_len:]
            market_closes = market_closes[-min_len:]

            stock_returns = [(stock_closes[i] - stock_closes[i-1]) / stock_closes[i-1] for i in range(1, len(stock_closes))]
            market_returns = [(market_closes[i] - market_closes[i-1]) / market_closes[i-1] for i in range(1, len(market_closes))]

            n = len(stock_returns)
            mean_stock = sum(stock_returns) / n
            mean_market = sum(market_returns) / n

            cov = sum((stock_returns[i] - mean_stock) * (market_returns[i] - mean_market) for i in range(n)) / (n - 1)
            var_market = sum((market_returns[i] - mean_market) ** 2 for i in range(n)) / (n - 1)
            beta = cov / var_market

            print(f"   Beta: {beta:.3f}")
    except Exception as e:
        print(f"   Beta Error: {e}")

    # 3. Historical Volatility
    print(f"\n3. Calculating Historical Volatility for {ticker}...")
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            response = await client.get(url, params={"interval": "1d", "range": "3mo"}, headers=HEADERS, timeout=10)
            data = response.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None][-30:]
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            hv = statistics.stdev(returns) * (252 ** 0.5) * 100
            print(f"   Historical Volatility (30d): {hv:.2f}%")
    except Exception as e:
        print(f"   HV Error: {e}")

    # 4. Implied Volatility (requires Alpha Vantage API key or options data access)
    print(f"\n4. Implied Volatility for {ticker}...")
    print("   Note: Yahoo options API requires auth. Use ALPHA_VANTAGE_API_KEY for IV data.")
    print("   Skipping IV test (optional metric).")

    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "TSLA"
    asyncio.run(test_all(ticker))
