"""
News Basket MCP Server

Web search API for AI agents - provides real-time news, articles, and web content.
Use cases:
- Company news and sentiment
- Industry trends
- Competitor analysis
- Going concern news coverage

API Documentation: https://docs.tavily.com/
Free tier: 1,000 API credits/month
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


async def search_company_news(ticker: str, company_name: str = None) -> dict:
    """
    Search for recent news about a company.
    """
    query = f"{ticker} stock news"
    if company_name:
        query = f"{company_name} ({ticker}) stock news"

    result = await tavily_search(
        query=query,
        search_depth="basic",
        max_results=5,
        exclude_domains=["reddit.com", "twitter.com", "x.com"],
    )

    # Add SWOT categorization
    if "results" in result and result["results"]:
        swot_hints = {
            "opportunities": [],
            "threats": []
        }

        for r in result["results"]:
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
    """List available Tavily tools."""
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
            name="search_company_news",
            description="Search for recent news about a company. Returns news with SWOT hints.",
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
