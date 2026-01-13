"""
News Basket MCP Server

Web search API for AI agents - provides real-time news, articles, and web content.
Use cases:
- Company news and sentiment
- Industry trends
- Competitor analysis
- Going concern news coverage

Data Sources:
- Tavily API: https://docs.tavily.com/ (1,000 credits/month free)
- NYT Article Search API: https://developer.nytimes.com/ (500 req/day free)
- NewsAPI: https://newsapi.org/ (100 req/day free, 24hr delay)
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone


def normalize_date(date_str: str) -> str:
    """Extract date-only (YYYY-MM-DD) from various datetime formats."""
    if not date_str:
        return None
    # Handle ISO format with/without timezone
    if "T" in date_str:
        return date_str.split("T")[0]
    # Already date-only
    if len(date_str) == 10:
        return date_str
    return date_str[:10] if len(date_str) >= 10 else date_str
from pathlib import Path
from typing import Optional

# Import company name normalization from shared configs, domain filters from local config
from configs.company_name_filters import clean_company_name
from config.domain_filters import NEWS_DOMAINS, NYT_NEWS_DESKS, NEWSAPI_DOMAINS

# Load environment variables (later files override earlier ones)
from dotenv import load_dotenv
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
logger = logging.getLogger("news-basket")

# Initialize MCP server
server = Server("news-basket")

# Tavily API configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_BASE_URL = "https://api.tavily.com"

# NYT Article Search API configuration
NYT_API_KEY = os.getenv("NYT_API_KEY")
NYT_BASE_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

# NewsAPI configuration (24hr lag on free tier)
NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")
NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"


# ============================================================
# SEARCH FUNCTIONS
# ============================================================

async def tavily_search(
    query: str,
    search_depth: str = "basic",
    max_results: int = 5,
    include_domains: list = None,
    exclude_domains: list = None,
    include_answer: bool = True,
    days: int = None,
) -> dict:
    """
    Execute Tavily search.

    Args:
        query: Search query
        search_depth: "basic" (faster) or "advanced" (more thorough)
        max_results: Number of results (1-10)
        include_domains: Limit to specific domains
        exclude_domains: Exclude specific domains
        include_answer: Include AI-generated answer
        days: Limit results to last N days (optional)
    """
    if not TAVILY_API_KEY:
        return {
            "error": "TAVILY_API_KEY not configured",
            "message": "Add TAVILY_API_KEY to ~/.env file. Get free key at https://tavily.com"
        }

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": search_depth,
                "max_results": min(max_results, 10),
                "include_answer": include_answer,
                "include_raw_content": False,
            }

            if include_domains:
                payload["include_domains"] = include_domains
            if exclude_domains:
                payload["exclude_domains"] = exclude_domains
            if days:
                payload["days"] = days

            response = await client.post(
                f"{TAVILY_BASE_URL}/search",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    "error": f"Tavily API error: {response.status_code}",
                    "message": response.text
                }

            data = response.json()

            # Format results
            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": r.get("content"),
                    "score": r.get("score"),
                    "published_date": r.get("published_date"),
                })

            return {
                "query": query,
                "answer": data.get("answer"),
                "results": results,
                "result_count": len(results),
                "search_depth": search_depth,
                "source": "Tavily",
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }

    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {"error": str(e)}


async def nyt_search(
    query: str,
    max_results: int = 5,
    sort: str = "newest",
    begin_date: str = None,
    end_date: str = None,
    news_desks: list[str] = None,
) -> dict:
    """
    Search NYT Article Search API.

    Args:
        query: Search query
        max_results: Number of results (max 10 per page)
        sort: "newest", "oldest", or "relevance"
        begin_date: Filter start date (YYYYMMDD)
        end_date: Filter end date (YYYYMMDD)
        news_desks: Filter by news desk (e.g., ["Business", "Technology"])

    Returns:
        Dict with articles from New York Times
    """
    if not NYT_API_KEY:
        return {
            "error": "NYT_API_KEY not configured",
            "message": "Add NYT_API_KEY to ~/.env file. Get free key at https://developer.nytimes.com/"
        }

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "api-key": NYT_API_KEY,
                "q": query,
                "sort": sort,
                "page": 0,
            }

            if begin_date:
                params["begin_date"] = begin_date
            if end_date:
                params["end_date"] = end_date
            if news_desks:
                # Filter by news desk: fq=news_desk:("Business" "Technology")
                desks_str = " ".join(f'"{desk}"' for desk in news_desks)
                params["fq"] = f"news_desk:({desks_str})"

            response = await client.get(
                NYT_BASE_URL,
                params=params,
                timeout=30
            )

            if response.status_code == 429:
                return {
                    "error": "NYT rate limit exceeded",
                    "message": "Rate limit: 5 req/min, 500 req/day"
                }

            if response.status_code != 200:
                return {
                    "error": f"NYT API error: {response.status_code}",
                    "message": response.text
                }

            data = response.json()
            docs = data.get("response", {}).get("docs") or []

            # Format results
            results = []
            for doc in docs[:max_results]:
                headline = doc.get("headline", {})
                results.append({
                    "title": headline.get("main", ""),
                    "url": doc.get("web_url", ""),
                    "content": doc.get("snippet", "") or doc.get("lead_paragraph", ""),
                    "published_date": doc.get("pub_date", ""),
                    "section": doc.get("section_name", ""),
                    "source": "New York Times",
                })

            return {
                "query": query,
                "results": results,
                "result_count": len(results),
                "total_hits": data.get("response", {}).get("meta", {}).get("hits", 0),
                "source": "NYT Article Search API",
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }

    except Exception as e:
        logger.error(f"NYT search error: {e}")
        return {"error": str(e)}


async def newsapi_search(
    query: str,
    max_results: int = 5,
    sort_by: str = "publishedAt",
    language: str = "en",
    domains: str = None,
) -> dict:
    """
    Search NewsAPI.org for articles.

    Args:
        query: Search query
        max_results: Number of results (max 100)
        sort_by: "publishedAt", "relevancy", or "popularity"
        language: Language code (e.g., "en")

    Returns:
        Dict with articles from 150,000+ sources

    Note: Free tier has 24-hour delay on articles
    """
    if not NEWSAPI_API_KEY:
        return {
            "error": "NEWSAPI_API_KEY not configured",
            "message": "Add NEWSAPI_API_KEY to ~/.env file. Get free key at https://newsapi.org/"
        }

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "apiKey": NEWSAPI_API_KEY,
                "q": query,
                "sortBy": sort_by,
                "language": language,
                "pageSize": min(max_results, 100),
            }
            if domains:
                params["domains"] = domains

            response = await client.get(
                NEWSAPI_BASE_URL,
                params=params,
                timeout=30
            )

            if response.status_code == 426:
                return {
                    "error": "NewsAPI requires paid plan for this request",
                    "message": "Free tier limited to 24hr old articles"
                }

            if response.status_code != 200:
                return {
                    "error": f"NewsAPI error: {response.status_code}",
                    "message": response.text
                }

            data = response.json()

            if data.get("status") != "ok":
                return {
                    "error": data.get("code", "Unknown error"),
                    "message": data.get("message", "")
                }

            # Format results
            results = []
            for art in data.get("articles", [])[:max_results]:
                results.append({
                    "title": art.get("title", ""),
                    "url": art.get("url", ""),
                    "content": art.get("description", "") or art.get("content", ""),
                    "published_date": art.get("publishedAt", ""),
                    "source": art.get("source", {}).get("name", "NewsAPI"),
                })

            return {
                "query": query,
                "results": results,
                "result_count": len(results),
                "total_hits": data.get("totalResults", 0),
                "source": "NewsAPI",
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }

    except Exception as e:
        logger.error(f"NewsAPI search error: {e}")
        return {"error": str(e)}


async def get_all_sources_news(ticker: str, company_name: str = None) -> dict:
    """
    Search for recent news about a company using Tavily, NYT, and NewsAPI.
    Combines results from all sources for comprehensive coverage.
    """
    # Build specific queries for better relevance
    base_query = f"{ticker} stock news"
    if company_name:
        base_query = f"{company_name} ({ticker}) stock news"

    # Tavily query - general search
    tavily_query = base_query

    # NYT query - cleaned company name + "stock" for disambiguation (e.g., Apple vs apple fruit)
    nyt_query = f"{clean_company_name(company_name or ticker)} stock"

    # NewsAPI query - ticker symbol helps filter
    newsapi_query = f"{company_name or ticker} {ticker} stock"

    # Calculate 7-day lookback
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

    # Fetch from all sources in parallel (limited to business/finance/tech domains)
    tavily_task = tavily_search(
        query=tavily_query,
        search_depth="basic",
        max_results=4,
        include_domains=NEWS_DOMAINS,
        exclude_domains=["reddit.com", "twitter.com", "x.com"],
        days=7,
    )

    nyt_task = nyt_search(
        query=nyt_query,
        max_results=5,
        sort="relevance",
        begin_date=seven_days_ago,
        news_desks=NYT_NEWS_DESKS,
    )

    newsapi_task = newsapi_search(
        query=newsapi_query,
        max_results=3,
        sort_by="publishedAt",
        domains=NEWSAPI_DOMAINS,
    )

    tavily_result, nyt_result, newsapi_result = await asyncio.gather(
        tavily_task, nyt_task, newsapi_task
    )

    # Build source-keyed structure
    result = {}

    # Add Tavily results
    if "results" in tavily_result and tavily_result["results"]:
        result["tavily"] = [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "content": a.get("content"),
                "published_date": normalize_date(a.get("published_date")),
            }
            for a in tavily_result["results"]
        ]

    # Add NYT results
    if "results" in nyt_result and nyt_result["results"]:
        result["nyt"] = [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "content": a.get("content") or a.get("snippet"),
                "published_date": normalize_date(a.get("published_date")),
            }
            for a in nyt_result["results"]
        ]

    # Add NewsAPI results
    if "results" in newsapi_result and newsapi_result["results"]:
        result["newsapi"] = [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "content": a.get("content"),
                "published_date": normalize_date(a.get("published_date")),
            }
            for a in newsapi_result["results"]
        ]

    return result


async def search_going_concern_news(ticker: str, company_name: str = None) -> dict:
    """
    Search for going concern or financial distress news about a company.
    """
    search_term = company_name or ticker
    query = f'"{search_term}" ("going concern" OR "substantial doubt" OR "bankruptcy" OR "liquidity crisis" OR "financial distress")'

    result = await tavily_search(
        query=query,
        search_depth="advanced",
        max_results=10,
        exclude_domains=["reddit.com", "twitter.com", "x.com"],
    )

    # Analyze for risk signals
    if "results" in result:
        risk_level = "none"
        risk_signals = []

        for r in result["results"]:
            content = (r.get("content") or "").lower()
            title = (r.get("title") or "").lower()

            if "going concern" in content or "going concern" in title:
                risk_signals.append({"type": "going_concern", "source": r["title"][:60]})
            if "bankruptcy" in content or "bankruptcy" in title:
                risk_signals.append({"type": "bankruptcy", "source": r["title"][:60]})
            if "substantial doubt" in content:
                risk_signals.append({"type": "substantial_doubt", "source": r["title"][:60]})

        if len(risk_signals) >= 3:
            risk_level = "high"
        elif len(risk_signals) >= 1:
            risk_level = "medium"

        result["risk_assessment"] = {
            "risk_level": risk_level,
            "signals_found": len(risk_signals),
            "signals": risk_signals[:5],
        }

    return result


async def search_industry_trends(industry: str) -> dict:
    """
    Search for industry trends and outlook.
    """
    query = f"{industry} industry trends outlook 2024 2025"

    result = await tavily_search(
        query=query,
        search_depth="advanced",
        max_results=8,
    )

    return result


async def search_competitor_news(ticker: str, competitors: list) -> dict:
    """
    Search for news about competitors.
    """
    competitor_str = " OR ".join(competitors)
    query = f"({competitor_str}) stock news market"

    result = await tavily_search(
        query=query,
        search_depth="basic",
        max_results=5,
    )

    return result


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

@server.list_tools()
async def list_tools():
    """List available news search tools (Tavily + NYT)."""
    return [
        Tool(
            name="tavily_search",
            description="General web search using Tavily API. Returns relevant articles with AI-generated answer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "description": "Search depth: basic (fast) or advanced (thorough)",
                        "default": "basic"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results (1-10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="nyt_search",
            description="Search New York Times articles. High-quality financial journalism.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (company name, topic, etc.)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results (1-10)",
                        "default": 5
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["newest", "oldest", "relevance"],
                        "description": "Sort order",
                        "default": "newest"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_all_sources_news",
            description="Search for recent news about a company from Tavily + NYT. Returns news with SWOT hints.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Full company name (optional, improves results)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="search_going_concern_news",
            description="Search for going concern, bankruptcy, or financial distress news about a company.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Full company name (optional)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="search_industry_trends",
            description="Search for industry trends and outlook.",
            inputSchema={
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "Industry name (e.g., 'semiconductor', 'electric vehicles', 'cloud computing')"
                    }
                },
                "required": ["industry"]
            }
        ),
        Tool(
            name="search_competitor_news",
            description="Search for news about competitor companies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Primary company ticker"
                    },
                    "competitors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of competitor tickers or names"
                    }
                },
                "required": ["ticker", "competitors"]
            }
        )
    ]


# Global timeout for all tool operations (seconds)
TOOL_TIMEOUT = 90.0  # Match mcp_client timeout


async def _execute_tool_with_timeout(name: str, arguments: dict) -> dict:
    """Execute a tool with timeout. Returns result dict or error dict."""
    if name == "tavily_search":
        query = arguments.get("query", "")
        search_depth = arguments.get("search_depth", "basic")
        max_results = arguments.get("max_results", 5)
        return await tavily_search(query, search_depth, max_results)
    elif name == "nyt_search":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        sort = arguments.get("sort", "newest")
        return await nyt_search(query, max_results, sort)
    elif name == "get_all_sources_news":
        ticker = arguments.get("ticker", "").upper()
        company_name = arguments.get("company_name")
        return await get_all_sources_news(ticker, company_name)
    elif name == "search_going_concern_news":
        ticker = arguments.get("ticker", "").upper()
        company_name = arguments.get("company_name")
        return await search_going_concern_news(ticker, company_name)
    elif name == "search_industry_trends":
        industry = arguments.get("industry", "")
        return await search_industry_trends(industry)
    elif name == "search_competitor_news":
        ticker = arguments.get("ticker", "").upper()
        competitors = arguments.get("competitors", [])
        return await search_competitor_news(ticker, competitors)
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
                "source": "news-basket",
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
            "source": "news-basket"
        }))]

    except Exception as e:
        # Catch-all: ALWAYS return valid JSON-RPC response
        logger.error(f"Unexpected error in {name}: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "ticker": arguments.get("ticker", ""),
            "tool": name,
            "source": "news-basket",
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
