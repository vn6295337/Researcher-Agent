"""
Sentiment Basket MCP Server

Aggregates sentiment metrics from multiple free sources for SWOT analysis:
- Finnhub News Sentiment → News articles analyzed with VADER
- Reddit → Retail investor sentiment from r/WallStreetBets, r/stocks

Usage:
    python server.py

Or via MCP:
    Add to claude_desktop_config.json
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

# Load environment variables from .env
from dotenv import load_dotenv

# Try loading from multiple locations
env_paths = [
    Path.home() / ".env",  # Home directory
    Path(__file__).parent / ".env",  # MCP server directory
    Path(__file__).parent.parent.parent / ".env",  # Project root
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Data fetching
import httpx

# Sentiment analysis
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentiment-basket")

# Initialize MCP server
server = Server("sentiment-basket")

# API Keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")  # Get free key: https://finnhub.io/register

# Initialize VADER if available
vader = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None


# ============================================================
# DATA FETCHERS
# ============================================================

async def fetch_finnhub_sentiment(ticker: str) -> dict:
    """
    Fetch company news from Finnhub and compute sentiment with VADER.
    Uses free company-news endpoint + local NLP analysis.
    """
    if not FINNHUB_API_KEY:
        return {
            "metric": "Finnhub News Sentiment",
            "ticker": ticker,
            "error": "FINNHUB_API_KEY not configured. Get free key at https://finnhub.io/register"
        }

    if not VADER_AVAILABLE:
        return {
            "metric": "Finnhub News Sentiment",
            "ticker": ticker,
            "error": "VADER sentiment analyzer not installed. Run: pip install vaderSentiment"
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
                    "metric": "Finnhub News Sentiment",
                    "ticker": ticker,
                    "error": data.get("error", "Unknown error")
                }

            if not data or not isinstance(data, list):
                return {
                    "metric": "Finnhub News Sentiment",
                    "ticker": ticker.upper(),
                    "score": 50,
                    "articles_analyzed": 0,
                    "interpretation": "No recent news articles found",
                    "swot_category": "NEUTRAL",
                    "source": "Finnhub",
                    "as_of": datetime.now().isoformat()
                }

            # Analyze sentiment of headlines with VADER
            total_score = 0
            for article in data[:50]:  # Limit to 50 articles
                headline = article.get("headline", "")
                summary = article.get("summary", "")
                text = f"{headline} {summary}"
                scores = vader.polarity_scores(text)
                total_score += scores["compound"]

            articles_count = min(len(data), 50)
            avg_sentiment = total_score / articles_count if articles_count > 0 else 0
            score = (avg_sentiment + 1) * 50  # Convert -1..1 to 0..100

            # Interpretation
            if score >= 60:
                interpretation = "Bullish sentiment - Positive news coverage"
                swot_impact = "STRENGTH"
            elif score >= 45:
                interpretation = "Neutral sentiment - Mixed news coverage"
                swot_impact = "NEUTRAL"
            elif score >= 30:
                interpretation = "Bearish sentiment - Negative news coverage"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very bearish sentiment - Predominantly negative coverage"
                swot_impact = "THREAT"

            return {
                "metric": "Finnhub News Sentiment",
                "ticker": ticker.upper(),
                "score": round(score, 2),
                "sentiment_raw": round(avg_sentiment, 3),
                "articles_analyzed": articles_count,
                "total_articles": len(data),
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Finnhub + VADER",
                "as_of": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Finnhub sentiment error for {ticker}: {e}")
        return {
            "metric": "Finnhub News Sentiment",
            "ticker": ticker,
            "error": str(e)
        }


async def fetch_reddit_sentiment(ticker: str, company_name: str = "") -> dict:
    """
    Fetch Reddit sentiment using public JSON endpoints.
    Searches r/WallStreetBets, r/stocks for mentions.
    Uses VADER for sentiment scoring (100 req/min rate limit).
    """
    if not VADER_AVAILABLE:
        return {
            "metric": "Reddit Sentiment",
            "ticker": ticker,
            "error": "VADER sentiment analyzer not installed"
        }

    try:
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": "SentimentBasket/1.0"}

            subreddits = ["wallstreetbets", "stocks"]
            all_texts = []
            total_score = 0
            total_upvotes = 0
            post_count = 0

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

                    text = f"{title} {selftext}"

                    # VADER sentiment
                    scores = vader.polarity_scores(text)
                    total_score += scores["compound"] * upvotes
                    total_upvotes += upvotes
                    post_count += 1

            if post_count == 0:
                return {
                    "metric": "Reddit Sentiment",
                    "ticker": ticker.upper(),
                    "score": 50,  # Neutral default
                    "posts_analyzed": 0,
                    "interpretation": "No recent posts found - Insufficient data",
                    "swot_category": "NEUTRAL",
                    "source": "Reddit (Public)",
                    "as_of": datetime.now().isoformat()
                }

            avg_sentiment = (total_score / total_upvotes) if total_upvotes > 0 else 0
            score = (avg_sentiment + 1) * 50

            if score >= 65:
                interpretation = "Bullish retail sentiment"
                swot_impact = "STRENGTH"
            elif score >= 50:
                interpretation = "Neutral retail sentiment"
                swot_impact = "NEUTRAL"
            elif score >= 35:
                interpretation = "Bearish retail sentiment"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very bearish retail sentiment"
                swot_impact = "THREAT"

            return {
                "metric": "Reddit Sentiment",
                "ticker": ticker.upper(),
                "score": round(score, 2),
                "sentiment_raw": round(avg_sentiment, 3),
                "posts_analyzed": post_count,
                "total_upvotes": total_upvotes,
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Reddit (Public)",
                "as_of": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Reddit public sentiment error: {e}")
        return {
            "metric": "Reddit Sentiment",
            "ticker": ticker,
            "error": str(e)
        }


async def get_full_sentiment_basket(ticker: str, company_name: str = "") -> dict:
    """
    Fetch all sentiment metrics for a given ticker/company.
    Returns aggregated SWOT-ready data.
    """
    if not company_name:
        company_name = ticker  # Use ticker as fallback

    # Fetch all metrics concurrently
    finnhub_task = fetch_finnhub_sentiment(ticker)
    reddit_task = fetch_reddit_sentiment(ticker, company_name)

    finnhub, reddit = await asyncio.gather(finnhub_task, reddit_task)

    # Aggregate SWOT impacts
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    # Calculate composite score (weighted average)
    scores = []
    weights = []

    for metric, weight in [(finnhub, 0.5), (reddit, 0.5)]:
        if "error" not in metric and "score" in metric:
            scores.append(metric["score"])
            weights.append(weight)

            impact = metric.get("swot_category", "NEUTRAL")
            desc = f"{metric['metric']}: {metric.get('score', 'N/A')}/100 - {metric.get('interpretation', '')}"

            if impact == "STRENGTH":
                swot_summary["strengths"].append(desc)
            elif impact == "WEAKNESS":
                swot_summary["weaknesses"].append(desc)
            elif impact == "OPPORTUNITY":
                swot_summary["opportunities"].append(desc)
            elif impact in ["THREAT", "SEVERE_THREAT"]:
                swot_summary["threats"].append(desc)

    # Calculate weighted composite score
    if scores and weights:
        total_weight = sum(weights)
        composite_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
    else:
        composite_score = 50  # Neutral default

    # Overall interpretation
    if composite_score >= 65:
        overall = "Overall Bullish Sentiment"
        overall_swot = "STRENGTH"
    elif composite_score >= 50:
        overall = "Overall Neutral Sentiment"
        overall_swot = "NEUTRAL"
    elif composite_score >= 35:
        overall = "Overall Bearish Sentiment"
        overall_swot = "WEAKNESS"
    else:
        overall = "Overall Very Bearish Sentiment"
        overall_swot = "THREAT"

    return {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "composite_score": round(composite_score, 2),
        "overall_interpretation": overall,
        "overall_swot_category": overall_swot,
        "metrics": {
            "finnhub": finnhub,
            "reddit": reddit
        },
        "swot_summary": swot_summary,
        "generated_at": datetime.now().isoformat()
    }


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

@server.list_tools()
async def list_tools():
    """List available sentiment tools."""
    return [
        Tool(
            name="get_finnhub_sentiment",
            description="Get news sentiment from Finnhub company news analyzed with VADER. Returns sentiment score (0-100).",
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
            name="get_reddit_sentiment",
            description="Get retail investor sentiment from Reddit (r/WallStreetBets, r/stocks). Uses VADER NLP for scoring.",
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
            description="Get full sentiment basket (Finnhub + Reddit) with composite score and SWOT summary.",
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


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool invocations."""
    try:
        if name == "get_finnhub_sentiment":
            ticker = arguments.get("ticker", "").upper()
            if not ticker:
                return [TextContent(type="text", text="Error: ticker is required")]
            result = await fetch_finnhub_sentiment(ticker)

        elif name == "get_reddit_sentiment":
            ticker = arguments.get("ticker", "").upper()
            company_name = arguments.get("company_name", "")
            if not ticker:
                return [TextContent(type="text", text="Error: ticker is required")]
            result = await fetch_reddit_sentiment(ticker, company_name)

        elif name == "get_sentiment_basket":
            ticker = arguments.get("ticker", "").upper()
            company_name = arguments.get("company_name", "")
            if not ticker:
                return [TextContent(type="text", text="Error: ticker is required")]
            result = await get_full_sentiment_basket(ticker, company_name)

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Tool error {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================
# MAIN
# ============================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
