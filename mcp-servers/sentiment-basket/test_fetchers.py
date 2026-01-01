"""
Test script for Sentiment Basket data fetchers.

Usage:
    python test_fetchers.py
"""

import asyncio
import json
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_paths = [
    Path.home() / ".env",
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

from server import (
    fetch_finnhub_sentiment,
    fetch_reddit_sentiment,
    get_full_sentiment_basket,
    FINNHUB_API_KEY,
    VADER_AVAILABLE
)


def print_result(name: str, result: dict):
    """Pretty print a result."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2))


async def test_finnhub(ticker: str = "AAPL"):
    """Test Finnhub sentiment fetcher."""
    print(f"\n[Finnhub] API Key configured: {'Yes' if FINNHUB_API_KEY else 'No'}")
    result = await fetch_finnhub_sentiment(ticker)
    print_result(f"Finnhub Sentiment - {ticker}", result)
    return result


async def test_reddit(ticker: str = "AAPL"):
    """Test Reddit sentiment fetcher (public endpoint, 100 req/min)."""
    print(f"\n[Reddit] VADER available: {'Yes' if VADER_AVAILABLE else 'No'}")
    result = await fetch_reddit_sentiment(ticker)
    print_result(f"Reddit Sentiment - {ticker}", result)
    return result


async def test_full_basket(ticker: str = "AAPL", company_name: str = "Apple"):
    """Test full sentiment basket."""
    print(f"\n[Full Basket] Testing {ticker} ({company_name})")
    result = await get_full_sentiment_basket(ticker, company_name)
    print_result(f"Full Sentiment Basket - {ticker}", result)
    return result


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("  SENTIMENT BASKET - TEST SUITE")
    print("="*60)

    # Check prerequisites
    print("\n[Prerequisites]")
    print(f"  VADER Sentiment: {'Installed' if VADER_AVAILABLE else 'NOT INSTALLED - pip install vaderSentiment'}")
    print(f"  FINNHUB_API_KEY: {'Set' if FINNHUB_API_KEY else 'Not set'}")

    # Run tests
    ticker = "TSLA"
    company = "Tesla"

    print(f"\n\nTesting with: {ticker} ({company})")
    print("-" * 40)

    await test_finnhub(ticker)
    await test_reddit(ticker)
    await test_full_basket(ticker, company)

    print("\n" + "="*60)
    print("  TEST SUITE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
