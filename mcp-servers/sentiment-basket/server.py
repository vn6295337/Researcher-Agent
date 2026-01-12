"""
Sentiment Basket MCP Server

Aggregates raw content from multiple sources for downstream sentiment analysis:
- Finnhub News → Raw news articles with headlines
- Reddit → Retail investor posts from r/WallStreetBets, r/stocks

Note: VADER sentiment scoring removed - apply sentiment analysis downstream.

Usage:
    python server.py

Or via MCP:
    Add to claude_desktop_config.json
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load environment variables from .env
from dotenv import load_dotenv

# Load from multiple locations (later files override earlier ones)
env_paths = [
    Path.home() / ".env",  # Home directory (base)
    Path(__file__).parent.parent.parent / ".env",  # Project root (overrides)
    Path(__file__).parent / ".env",  # MCP server directory (highest priority)
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Data fetching
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentiment-basket")

# Initialize MCP server
server = Server("sentiment-basket")

# API Keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")  # Get free key: https://finnhub.io/register


# ============================================================
# DATA FETCHERS
# ============================================================

async def fetch_finnhub_news(ticker: str) -> dict:
    """
    Fetch company news from Finnhub.
    Returns raw articles without sentiment scoring.
    """
    if not FINNHUB_API_KEY:
        return {
            "metric": "Finnhub News",
            "ticker": ticker,
            "error": "FINNHUB_API_KEY not configured. Get free key at https://finnhub.io/register"
        }

    try:
        async with httpx.AsyncClient() as client:
            # Get company news (free tier)
            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            url = "https://finnhub.io/api/v1/company-news"
            params = {
                "symbol": ticker.upper(),
                "from": week_ago,
                "to": today,
                "token": FINNHUB_API_KEY
            }
            response = await client.get(url, params=params, timeout=10)
            data = response.json()

            if isinstance(data, dict) and "error" in data:
                return {
                    "metric": "Finnhub News",
                    "ticker": ticker,
                    "error": data.get("error", "Unknown error")
                }

            if not data or not isinstance(data, list):
                return {
                    "metric": "Finnhub News",
                    "ticker": ticker.upper(),
                    "articles_count": 0,
                    "articles": [],
                    "source": "Finnhub",
                    "as_of": datetime.now().strftime("%Y-%m-%d")
                }

            # Return raw articles without sentiment scoring
            articles_list = []
            for article in data[:50]:  # Limit to 50 articles
                articles_list.append({
                    "headline": article.get("headline", ""),
                    "summary": article.get("summary", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "datetime": datetime.fromtimestamp(article.get("datetime", 0), tz=timezone.utc).strftime("%Y-%m-%d") if article.get("datetime") else None,
                })

            return {
                "metric": "Finnhub News",
                "ticker": ticker.upper(),
                "articles_count": len(articles_list),
                "total_articles": len(data),
                "source": "Finnhub",
                "articles": articles_list,
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }

    except Exception as e:
        logger.error(f"Finnhub news error for {ticker}: {e}")
        return {
            "metric": "Finnhub News",
            "ticker": ticker,
            "error": str(e)
        }


async def fetch_reddit_posts(ticker: str, company_name: str = "") -> dict:
    """
    Fetch Reddit posts using public JSON endpoints.
    Searches r/WallStreetBets, r/stocks for mentions.
    Returns raw posts without sentiment scoring.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": "SentimentBasket/1.0"}

            subreddits = ["wallstreetbets", "stocks"]
            posts_list = []
            total_upvotes = 0

            search_query = ticker.upper()

            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    "q": search_query,
                    "sort": "relevance",
                    "t": "week",
                    "limit": 10,
                    "restrict_sr": "true"
                }

                try:
                    response = await client.get(url, headers=headers, params=params, timeout=10)
                    if response.status_code == 429:
                        continue  # Rate limited, skip this subreddit
                    data = response.json()
                except:
                    continue

                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")[:500]  # Limit text length
                    upvotes = post_data.get("ups", 1)
                    permalink = post_data.get("permalink", "")

                    total_upvotes += upvotes

                    # Capture post details with URL (no sentiment scoring)
                    posts_list.append({
                        "title": title,
                        "selftext": selftext,
                        "url": f"https://reddit.com{permalink}" if permalink else "",
                        "subreddit": f"r/{subreddit}",
                        "upvotes": upvotes,
                        "created_utc": datetime.fromtimestamp(post_data.get("created_utc", 0), tz=timezone.utc).strftime("%Y-%m-%d") if post_data.get("created_utc") else None
                    })

            return {
                "metric": "Reddit Posts",
                "ticker": ticker.upper(),
                "posts_count": len(posts_list),
                "total_upvotes": total_upvotes,
                "source": "Reddit (Public)",
                "posts": posts_list,
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }

    except Exception as e:
        logger.error(f"Reddit posts error: {e}")
        return {
            "metric": "Reddit Posts",
            "ticker": ticker,
            "error": str(e)
        }


async def get_all_sources_sentiment(ticker: str, company_name: str = "") -> dict:
    """
    Fetch raw content from all sources for a given ticker/company.
    Returns NORMALIZED schema for content_analysis group.
    Sentiment analysis should be applied downstream.
    """
    if not company_name:
        company_name = ticker  # Use ticker as fallback

    # Fetch from all sources concurrently
    finnhub_task = fetch_finnhub_news(ticker)
    reddit_task = fetch_reddit_posts(ticker, company_name)

    finnhub, reddit = await asyncio.gather(finnhub_task, reddit_task)

    # Build normalized content_analysis schema
    items = []
    sources_used = []

    # Add Finnhub articles
    if "error" not in finnhub and finnhub.get("articles"):
        sources_used.append("Finnhub")
        for article in finnhub.get("articles", []):
            items.append({
                "title": article.get("headline"),
                "content": article.get("summary"),
                "url": article.get("url"),
                "datetime": article.get("datetime"),
                "source": "Finnhub",
                "subreddit": None,  # Not applicable for Finnhub
            })

    # Add Reddit posts
    if "error" not in reddit and reddit.get("posts"):
        sources_used.append("Reddit")
        for post in reddit.get("posts", []):
            items.append({
                "title": post.get("title"),
                "content": post.get("selftext"),
                "url": post.get("url"),
                "datetime": post.get("created_utc"),
                "source": "Reddit",
                "subreddit": post.get("subreddit"),  # Separate subreddit field
            })

    # Sort by datetime (most recent first)
    items.sort(key=lambda x: x.get("datetime") or "", reverse=True)

    return {
        "group": "content_analysis",
        "ticker": ticker.upper(),
        "items": items,
        "item_count": len(items),
        "sources_used": sources_used,
        "source": "sentiment-basket",
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

@server.list_tools()
async def list_tools():
    """List available content fetching tools (no sentiment scoring)."""
    return [
        Tool(
            name="get_finnhub_news",
            description="Get news articles from Finnhub company news. Returns raw articles without sentiment scoring.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, TSLA)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_reddit_posts",
            description="Get retail investor posts from Reddit (r/WallStreetBets, r/stocks). Returns raw posts without sentiment scoring.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Optional company name for broader search"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_sentiment_basket",
            description="Get full content basket (Finnhub + Reddit) with raw articles/posts. No sentiment scoring - apply VADER downstream.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Company name (optional, defaults to ticker)"
                    }
                },
                "required": ["ticker"]
            }
        )
    ]


# Global timeout for all tool operations (seconds)
# Increased for completeness-first mode
TOOL_TIMEOUT = 90.0  # Match mcp_client timeout


async def _execute_tool_with_timeout(name: str, arguments: dict) -> dict:
    """Execute a tool with timeout. Returns result dict or error dict."""
    ticker = arguments.get("ticker", "").upper()
    company_name = arguments.get("company_name", "")

    if name == "get_finnhub_news":
        if not ticker:
            return {"error": "ticker is required"}
        return await fetch_finnhub_news(ticker)
    elif name == "get_reddit_posts":
        if not ticker:
            return {"error": "ticker is required"}
        return await fetch_reddit_posts(ticker, company_name)
    elif name == "get_sentiment_basket":
        if not ticker:
            return {"error": "ticker is required"}
        return await get_all_sources_sentiment(ticker, company_name)
    else:
        return {"error": f"Unknown tool: {name}"}


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """
    Handle tool invocations with GUARANTEED JSON-RPC response.

    This function ALWAYS returns a valid TextContent response, even if:
    - External APIs timeout
    - Exceptions occur during processing
    - Any unexpected error happens

    This ensures MCP protocol compliance and prevents client hangs.
    """
    try:
        # Execute tool with global timeout
        try:
            result = await asyncio.wait_for(
                _execute_tool_with_timeout(name, arguments),
                timeout=TOOL_TIMEOUT
            )
        except asyncio.TimeoutError:
            ticker = arguments.get("ticker", "")
            logger.error(f"Tool {name} timed out after {TOOL_TIMEOUT}s for {ticker}")
            result = {
                "error": f"Tool execution timed out after {TOOL_TIMEOUT} seconds",
                "ticker": ticker,
                "tool": name,
                "source": "sentiment-basket",
                "fallback": True
            }

        # Ensure result is JSON serializable
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except json.JSONDecodeError as e:
        logger.error(f"JSON serialization error for {name}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"JSON serialization failed: {str(e)}",
            "ticker": arguments.get("ticker", ""),
            "tool": name,
            "source": "sentiment-basket"
        }))]

    except Exception as e:
        # Catch-all: ALWAYS return valid JSON-RPC response
        logger.error(f"Unexpected error in {name}: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "ticker": arguments.get("ticker", ""),
            "tool": name,
            "source": "sentiment-basket",
            "fallback": True
        }))]


# ============================================================
# MAIN
# ============================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
