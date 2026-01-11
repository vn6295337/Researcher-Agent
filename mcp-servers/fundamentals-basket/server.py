"""
Fundamentals Basket MCP Server

Thin facade that delegates to microservices:
- OrchestratorService: Coordinates fetcher, parser, cache
- FetcherService: HTTP calls with retry, rate limiting, circuit breaker
- ParserService: XBRL parsing, ratio calculations
- CacheService: CIK and facts caching with TTL

This file only handles:
- MCP protocol (tool definitions, call_tool decorator)
- Response formatting
- Legacy tools not yet migrated (material_events, ownership_filings, going_concern)
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

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

# Services
from services.orchestrator import get_orchestrator_service
from services.cache import get_cache_service
from services.fetcher import get_fetcher_service
from config import TOOL_TIMEOUT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fundamentals-basket")

# Initialize MCP server
server = Server("fundamentals-basket")

# Get orchestrator service
orchestrator = get_orchestrator_service()


# =============================================================================
# LEGACY TOOLS (Not yet migrated to microservices)
# =============================================================================

async def fetch_material_events(ticker: str, limit: int = 20) -> dict:
    """
    Fetch recent 8-K material events (legacy implementation).

    Parses 8-K filings for material events like:
    - Item 1.02: Termination of material agreement
    - Item 1.03: Bankruptcy or receivership
    - Item 2.04: Asset impairment
    - Item 5.02: Executive changes
    """
    cache = get_cache_service()
    fetcher = get_fetcher_service()

    cik = await cache.get_cik(ticker.upper())
    if not cik:
        cik = await fetcher.fetch_cik(ticker)
        if cik:
            await cache.set_cik(ticker.upper(), cik)

    if not cik:
        return {"ticker": ticker.upper(), "error": "CIK not found", "events": []}

    try:
        submissions = await fetcher.fetch_company_submissions(cik)
        recent = submissions.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        items_list = recent.get("items", [])

        events = []
        eight_k_indices = [i for i, f in enumerate(forms) if f == "8-K"][:limit]

        # High-priority item codes
        high_priority_items = {
            "1.02": "Termination of material agreement",
            "1.03": "Bankruptcy or receivership",
            "2.04": "Asset impairment",
            "2.05": "Delisting",
            "2.06": "Material impairment",
            "3.01": "Notice of delisting",
            "4.01": "Changes in auditors",
            "4.02": "Non-reliance on financial statements",
            "5.02": "Executive changes",
        }

        for idx in eight_k_indices:
            items = items_list[idx] if idx < len(items_list) else ""
            item_codes = [i.strip() for i in items.split(",") if i.strip()]

            is_high_priority = any(
                code in high_priority_items for code in item_codes
            )

            events.append({
                "form": "8-K",
                "filing_date": dates[idx] if idx < len(dates) else None,
                "accession": accessions[idx] if idx < len(accessions) else None,
                "items": item_codes,
                "high_priority": is_high_priority,
                "descriptions": [
                    high_priority_items.get(code, f"Item {code}")
                    for code in item_codes
                    if code in high_priority_items
                ],
            })

        high_priority_count = sum(1 for e in events if e.get("high_priority"))

        return {
            "ticker": ticker.upper(),
            "total_8k_filings": len(eight_k_indices),
            "high_priority_events": high_priority_count,
            "events": events,
            "swot_implications": {
                "threats": [
                    f"Found {high_priority_count} high-priority material events"
                ] if high_priority_count > 0 else [],
            },
            "source": "SEC EDGAR",
        }

    except Exception as e:
        logger.error(f"Material events fetch error for {ticker}: {e}")
        return {"ticker": ticker.upper(), "error": str(e), "events": []}


async def fetch_ownership_filings(ticker: str, limit: int = 20) -> dict:
    """
    Fetch ownership filings (legacy implementation).

    Includes:
    - 13D/13G: 5%+ ownership changes
    - Form 4: Insider transactions
    """
    cache = get_cache_service()
    fetcher = get_fetcher_service()

    cik = await cache.get_cik(ticker.upper())
    if not cik:
        cik = await fetcher.fetch_cik(ticker)
        if cik:
            await cache.set_cik(ticker.upper(), cik)

    if not cik:
        return {"ticker": ticker.upper(), "error": "CIK not found"}

    try:
        submissions = await fetcher.fetch_company_submissions(cik)
        recent = submissions.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])

        # 13D/13G filings (5%+ owners)
        thirteen_d_forms = ["SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"]
        thirteen_d_indices = [
            i for i, f in enumerate(forms) if f in thirteen_d_forms
        ][:limit]

        ownership_filings = []
        for idx in thirteen_d_indices:
            ownership_filings.append({
                "form": forms[idx],
                "filing_date": dates[idx] if idx < len(dates) else None,
                "accession": accessions[idx] if idx < len(accessions) else None,
            })

        # Form 4 filings (insider trades)
        form4_indices = [i for i, f in enumerate(forms) if f == "4"][:limit]
        insider_filings = []
        for idx in form4_indices:
            insider_filings.append({
                "form": "4",
                "filing_date": dates[idx] if idx < len(dates) else None,
                "accession": accessions[idx] if idx < len(accessions) else None,
            })

        return {
            "ticker": ticker.upper(),
            "ownership_5pct_filings": {
                "count": len(ownership_filings),
                "filings": ownership_filings,
            },
            "insider_transactions": {
                "count": len(insider_filings),
                "filings": insider_filings,
            },
            "swot_implications": {
                "opportunities": [
                    f"Active institutional interest: {len(ownership_filings)} 13D/13G filings"
                ] if ownership_filings else [],
            },
            "source": "SEC EDGAR",
        }

    except Exception as e:
        logger.error(f"Ownership filings fetch error for {ticker}: {e}")
        return {"ticker": ticker.upper(), "error": str(e)}


async def fetch_going_concern(ticker: str) -> dict:
    """
    Search 10-K for going concern warnings (legacy implementation).

    Looks for keywords indicating substantial doubt about continuing operations.
    """
    cache = get_cache_service()
    fetcher = get_fetcher_service()

    cik = await cache.get_cik(ticker.upper())
    if not cik:
        cik = await fetcher.fetch_cik(ticker)
        if cik:
            await cache.set_cik(ticker.upper(), cik)

    if not cik:
        return {"ticker": ticker.upper(), "error": "CIK not found"}

    try:
        submissions = await fetcher.fetch_company_submissions(cik)
        recent = submissions.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        # Find latest 10-K
        ten_k_idx = None
        for i, f in enumerate(forms):
            if f in ["10-K", "10-K/A"]:
                ten_k_idx = i
                break

        if ten_k_idx is None:
            return {
                "ticker": ticker.upper(),
                "warning": "No 10-K filing found",
                "going_concern_found": False,
            }

        # Construct document URL
        accession = accessions[ten_k_idx].replace("-", "")
        doc = primary_docs[ten_k_idx]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{doc}"

        # Fetch document
        doc_text = await fetcher.fetch_10k_document(url)

        # Search for going concern keywords
        keywords = [
            "going concern",
            "substantial doubt",
            "ability to continue",
            "liquidity concerns",
            "material uncertainty",
        ]

        matches = []
        doc_lower = doc_text.lower()
        for keyword in keywords:
            if keyword in doc_lower:
                matches.append(keyword)

        # Determine risk level
        if len(matches) >= 3:
            risk_level = "high"
        elif len(matches) >= 1:
            risk_level = "medium"
        else:
            risk_level = "none"

        return {
            "ticker": ticker.upper(),
            "going_concern_found": len(matches) > 0,
            "risk_level": risk_level,
            "keywords_found": matches,
            "filing_url": url,
            "swot_implications": {
                "threats": [
                    f"Going concern warning: {', '.join(matches)}"
                ] if matches else [],
            },
            "source": "SEC EDGAR 10-K",
        }

    except Exception as e:
        logger.error(f"Going concern search error for {ticker}: {e}")
        return {"ticker": ticker.upper(), "error": str(e)}


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

@server.list_tools()
async def list_tools():
    """List available SEC EDGAR tools."""
    return [
        Tool(
            name="get_company_info",
            description="Get basic company information from SEC EDGAR (name, industry, CIK).",
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
            name="get_financials",
            description="Get key financial metrics from SEC filings (revenue, income, margins).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_debt_metrics",
            description="Get debt and leverage metrics (debt levels, debt-to-equity ratio).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_cash_flow",
            description="Get cash flow metrics (operating CF, CapEx, free cash flow, R&D).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_sec_fundamentals",
            description="Get complete SEC fundamentals basket with aggregated SWOT summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_material_events",
            description="Get recent 8-K material events (bankruptcy, impairments, executive changes, delisting).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent 8-K filings to return (default: 20)",
                        "default": 20
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_ownership_filings",
            description="Get ownership filings: 13D/13G (5%+ ownership changes), Form 4 (insider transactions).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of filings per category to return (default: 20)",
                        "default": 20
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_going_concern",
            description="Search latest 10-K for going concern warnings (substantial doubt, liquidity issues).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_all_sources_fundamentals",
            description="Get financials from ALL sources (SEC EDGAR + Yahoo Finance) for side-by-side comparison.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        )
    ]


# =============================================================================
# MCP CALL TOOL HANDLER
# =============================================================================

async def _execute_tool(name: str, ticker: str, arguments: dict) -> dict:
    """Execute a tool by name."""
    # Orchestrator-handled tools
    orchestrator_tools = {
        "get_company_info",
        "get_financials",
        "get_debt_metrics",
        "get_cash_flow",
        "get_sec_fundamentals",
        "get_all_sources_fundamentals",
    }

    if name in orchestrator_tools:
        return await orchestrator.execute_tool(name, {"ticker": ticker, **arguments})

    # Legacy tools
    if name == "get_material_events":
        limit = arguments.get("limit", 20)
        return await fetch_material_events(ticker, limit)

    elif name == "get_ownership_filings":
        limit = arguments.get("limit", 20)
        return await fetch_ownership_filings(ticker, limit)

    elif name == "get_going_concern":
        return await fetch_going_concern(ticker)

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
        ticker = arguments.get("ticker", "").upper()
        if not ticker:
            return [TextContent(type="text", text=json.dumps({
                "error": "ticker is required",
                "ticker": None,
                "source": "fundamentals-basket"
            }))]

        # Execute tool with global timeout
        try:
            result = await asyncio.wait_for(
                _execute_tool(name, ticker, arguments),
                timeout=TOOL_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"Tool {name} timed out after {TOOL_TIMEOUT}s for {ticker}")
            result = {
                "error": f"Tool execution timed out after {TOOL_TIMEOUT} seconds",
                "ticker": ticker,
                "tool": name,
                "source": "fundamentals-basket",
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
            "source": "fundamentals-basket"
        }))]

    except Exception as e:
        # Catch-all: ALWAYS return valid JSON-RPC response
        logger.error(f"Unexpected error in {name}: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "ticker": arguments.get("ticker", ""),
            "tool": name,
            "source": "fundamentals-basket",
            "fallback": True
        }))]


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the MCP server."""
    logger.info("Starting fundamentals-basket MCP server (microservices architecture)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
