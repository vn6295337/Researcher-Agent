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
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

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
                "as_of": datetime.now().isoformat()
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
) -> dict:
    """
    Search NYT Article Search API.

    Args:
        query: Search query
        max_results: Number of results (max 10 per page)
        sort: "newest", "oldest", or "relevance"
        begin_date: Filter start date (YYYYMMDD)
        end_date: Filter end date (YYYYMMDD)

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
            docs = data.get("response", {}).get("docs", [])

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
                "as_of": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"NYT search error: {e}")
        return {"error": str(e)}


async def search_company_news(ticker: str, company_name: str = None) -> dict:
    """
    Search for recent news about a company using Tavily and NYT APIs.
    Combines results from both sources for comprehensive coverage.
    """
    query = f"{ticker} stock news"
    if company_name:
        query = f"{company_name} ({ticker}) stock news"

    # Fetch from both sources in parallel
    tavily_task = tavily_search(
        query=query,
        search_depth="basic",
        max_results=5,
        exclude_domains=["reddit.com", "twitter.com", "x.com"],
    )

    nyt_query = company_name or ticker
    nyt_task = nyt_search(
        query=nyt_query,
        max_results=3,
        sort="newest",
    )

    tavily_result, nyt_result = await asyncio.gather(tavily_task, nyt_task)

    # Combine results
    all_results = []
    sources_used = []

    # Add Tavily results
    if "results" in tavily_result and tavily_result["results"]:
        all_results.extend(tavily_result["results"])
        sources_used.append("Tavily")

    # Add NYT results
    if "results" in nyt_result and nyt_result["results"]:
        all_results.extend(nyt_result["results"])
        sources_used.append("NYT")

    # Build combined result
    result = {
        "query": query,
        "answer": tavily_result.get("answer"),
        "results": all_results,
        "result_count": len(all_results),
        "sources": sources_used,
        "source": " + ".join(sources_used) if sources_used else "None",
        "as_of": datetime.now().isoformat()
    }

    # Add SWOT categorization
    if all_results:
        swot_hints = {
            "opportunities": [],
            "threats": []
        }

        for r in all_results:
            content = (r.get("content") or "").lower()
            title = (r.get("title") or "").lower()

            # Look for positive signals
            if any(kw in content or kw in title for kw in ["upgrade", "beat", "growth", "strong", "positive"]):
                swot_hints["opportunities"].append(r["title"][:80])

            # Look for negative signals
            if any(kw in content or kw in title for kw in ["downgrade", "miss", "decline", "weak", "concern", "warning"]):
                swot_hints["threats"].append(r["title"][:80])

        result["swot_hints"] = swot_hints

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

        result["swot_implications"] = {
            "threats": [f"News coverage of financial distress ({len(risk_signals)} articles)"] if risk_signals else []
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
            name="search_company_news",
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


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool invocations."""
    try:
        if name == "tavily_search":
            query = arguments.get("query", "")
            search_depth = arguments.get("search_depth", "basic")
            max_results = arguments.get("max_results", 5)
            result = await tavily_search(query, search_depth, max_results)

        elif name == "nyt_search":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            sort = arguments.get("sort", "newest")
            result = await nyt_search(query, max_results, sort)

        elif name == "search_company_news":
            ticker = arguments.get("ticker", "").upper()
            company_name = arguments.get("company_name")
            result = await search_company_news(ticker, company_name)

        elif name == "search_going_concern_news":
            ticker = arguments.get("ticker", "").upper()
            company_name = arguments.get("company_name")
            result = await search_going_concern_news(ticker, company_name)

        elif name == "search_industry_trends":
            industry = arguments.get("industry", "")
            result = await search_industry_trends(industry)

        elif name == "search_competitor_news":
            ticker = arguments.get("ticker", "").upper()
            competitors = arguments.get("competitors", [])
            result = await search_competitor_news(ticker, competitors)

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
