#!/usr/bin/env python3
"""
Test script for Tavily API (standalone, no MCP required).
Usage: python test_fetchers.py [query]
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

import httpx

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_BASE_URL = "https://api.tavily.com"


async def test_search(query: str):
    """Test Tavily search."""
    print(f"\n{'='*60}")
    print(f"Tavily Search Test")
    print(f"{'='*60}\n")

    if not TAVILY_API_KEY:
        print("ERROR: TAVILY_API_KEY not found in ~/.env")
        print("Get a free API key at: https://tavily.com")
        print("Add to ~/.env: TAVILY_API_KEY=your_key_here")
        return

    print(f"Query: {query}\n")

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": True,
            }

            response = await client.post(
                f"{TAVILY_BASE_URL}/search",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(response.text)
                return

            data = response.json()

            # Print answer
            if data.get("answer"):
                print("AI Answer:")
                print(f"  {data['answer'][:500]}...")
                print()

            # Print results
            print(f"Results ({len(data.get('results', []))}):")
            for i, r in enumerate(data.get("results", [])[:5], 1):
                print(f"\n  {i}. {r.get('title', 'No title')}")
                print(f"     URL: {r.get('url', 'N/A')}")
                content = r.get('content', '')[:150]
                print(f"     {content}...")

    except Exception as e:
        print(f"Error: {e}")

    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}\n")


async def test_company_news(ticker: str):
    """Test company news search."""
    print(f"\n{'='*60}")
    print(f"Company News Test: {ticker}")
    print(f"{'='*60}\n")

    if not TAVILY_API_KEY:
        print("ERROR: TAVILY_API_KEY not configured")
        return

    query = f"{ticker} stock news"

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": True,
                "exclude_domains": ["reddit.com", "twitter.com"],
            }

            response = await client.post(
                f"{TAVILY_BASE_URL}/search",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return

            data = response.json()

            print(f"Recent news for {ticker}:")
            for i, r in enumerate(data.get("results", [])[:5], 1):
                title = r.get('title', 'No title')[:70]
                print(f"  {i}. {title}")

    except Exception as e:
        print(f"Error: {e}")

    print()


async def test_going_concern(ticker: str):
    """Test going concern news search."""
    print(f"\n{'='*60}")
    print(f"Going Concern News Test: {ticker}")
    print(f"{'='*60}\n")

    if not TAVILY_API_KEY:
        print("ERROR: TAVILY_API_KEY not configured")
        return

    query = f'"{ticker}" ("going concern" OR "substantial doubt" OR "bankruptcy")'

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "max_results": 5,
                "include_answer": True,
            }

            response = await client.post(
                f"{TAVILY_BASE_URL}/search",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return

            data = response.json()

            results = data.get("results", [])
            if results:
                print(f"Found {len(results)} potential risk articles:")
                for i, r in enumerate(results[:5], 1):
                    title = r.get('title', 'No title')[:70]
                    print(f"  {i}. {title}")
            else:
                print("No going concern/bankruptcy news found (good sign)")

    except Exception as e:
        print(f"Error: {e}")

    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.upper() == arg and len(arg) <= 5:
            # Looks like a ticker
            asyncio.run(test_company_news(arg))
            asyncio.run(test_going_concern(arg))
        else:
            # General query
            asyncio.run(test_search(arg))
    else:
        asyncio.run(test_search("Apple stock news"))
