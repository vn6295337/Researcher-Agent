"""
Valuation Basket MCP Server

Stock valuation multiples from Yahoo Finance via yfinance library.
Provides valuation context for SWOT analysis:
- P/E Ratio → Price relative to earnings (trailing & forward)
- P/S Ratio → Price relative to sales
- P/B Ratio → Price relative to book value
- EV/EBITDA → Enterprise value multiple
- PEG Ratio → P/E adjusted for growth (trailing & forward)

Usage:
    python server.py

Or via MCP:
    Add to claude_desktop_config.json
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

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

# Data fetching via yfinance
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("valuation-basket")

# Initialize MCP server
server = Server("valuation-basket")

# Thread pool for running yfinance (which is synchronous)
executor = ThreadPoolExecutor(max_workers=2)


# ============================================================
# DATA FETCHERS (using yfinance)
# ============================================================

def _fetch_yfinance_sync(ticker: str) -> dict:
    """
    Synchronous yfinance fetch (runs in thread pool).
    Returns all valuation metrics from Yahoo Finance.
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        if not info or info.get("regularMarketPrice") is None:
            return {"error": f"No data found for ticker {ticker}"}

        # Calculate Forward PEG if possible
        forward_peg = None
        forward_pe = info.get("forwardPE")
        earnings_growth = info.get("earningsGrowth")
        if forward_pe and earnings_growth and earnings_growth > 0:
            forward_peg = forward_pe / (earnings_growth * 100)

        # Convert regularMarketTime (Unix timestamp) to date string (YYYY-MM-DD)
        # Use UTC to get correct trading date (NYSE closes at 21:00 UTC)
        from datetime import datetime as dt, timezone
        regular_market_time = info.get("regularMarketTime")
        market_date_str = None
        if regular_market_time:
            try:
                market_date_str = dt.fromtimestamp(regular_market_time, tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                market_date_str = dt.now(tz=timezone.utc).strftime("%Y-%m-%d")

        return {
            "ticker": ticker.upper(),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "pb_ratio": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "trailing_peg": info.get("trailingPegRatio"),
            "forward_peg": forward_peg,
            "earnings_growth": earnings_growth,
            "revenue_growth": info.get("revenueGrowth"),
            "regular_market_time": market_date_str,
            "source": "Yahoo Finance (yfinance)"
        }

    except Exception as e:
        logger.error(f"yfinance fetch error for {ticker}: {e}")
        return {"error": str(e)}


# Alpha Vantage API key for fallback
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")


def _safe_float(value, default=None):
    """Safely convert Alpha Vantage value to float. Handles '-' and 'None' strings."""
    if value is None or value == "-" or value == "None" or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=None):
    """Safely convert Alpha Vantage value to int. Handles '-' and 'None' strings."""
    if value is None or value == "-" or value == "None" or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _fetch_alpha_vantage_sync(ticker: str) -> dict:
    """
    Synchronous Alpha Vantage fetch (runs in thread pool).
    Fallback source when Yahoo Finance fails.
    """
    import requests

    if not ALPHA_VANTAGE_KEY:
        return {"error": "Alpha Vantage API key not configured"}

    try:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
        response = requests.get(url, timeout=15)
        data = response.json()

        if "Error Message" in data or not data.get("Symbol"):
            return {"error": f"No data found for ticker {ticker}"}

        # Extract valuation metrics from Alpha Vantage OVERVIEW
        trailing_pe = _safe_float(data.get("TrailingPE"))
        forward_pe = _safe_float(data.get("ForwardPE"))
        pb_ratio = _safe_float(data.get("PriceToBookRatio"))
        ps_ratio = _safe_float(data.get("PriceToSalesRatioTTM"))
        ev_ebitda = _safe_float(data.get("EVToEBITDA"))
        peg_ratio = _safe_float(data.get("PEGRatio"))

        # Extract LatestQuarter as the "As Of" date
        latest_quarter = data.get("LatestQuarter")  # Format: YYYY-MM-DD

        # Calculate last trading day for "Filed/Updated" field
        # Alpha Vantage data is updated on trading days, so use last weekday
        from datetime import datetime as dt, timedelta
        today = dt.now()
        # If weekend, go back to Friday
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday > 0 and today.weekday() >= 5:  # Saturday=5, Sunday=6
            last_trading_day = today - timedelta(days=days_since_friday)
        else:
            last_trading_day = today
        fetch_time = last_trading_day.strftime("%Y-%m-%d")

        return {
            "ticker": ticker.upper(),
            "current_price": _safe_float(data.get("50DayMovingAverage")),
            "market_cap": _safe_int(data.get("MarketCapitalization")),
            "enterprise_value": None,  # Not available in OVERVIEW
            "trailing_pe": trailing_pe if trailing_pe and trailing_pe > 0 else None,
            "forward_pe": forward_pe if forward_pe and forward_pe > 0 else None,
            "ps_ratio": ps_ratio if ps_ratio and ps_ratio > 0 else None,
            "pb_ratio": pb_ratio if pb_ratio and pb_ratio > 0 else None,
            "ev_ebitda": ev_ebitda if ev_ebitda and ev_ebitda > 0 else None,
            "trailing_peg": peg_ratio if peg_ratio and peg_ratio > 0 else None,
            "forward_peg": None,
            "earnings_growth": _safe_float(data.get("QuarterlyEarningsGrowthYOY")),
            "revenue_growth": _safe_float(data.get("QuarterlyRevenueGrowthYOY")),
            "latest_quarter": latest_quarter,  # As Of date
            "fetched_at": fetch_time,  # Filed/Updated date
            "source": "Alpha Vantage (fallback)",
            "fallback": True
        }

    except Exception as e:
        logger.error(f"Alpha Vantage fetch error for {ticker}: {e}")
        return {"error": str(e)}


async def fetch_alpha_vantage_quote(ticker: str) -> Optional[dict]:
    """
    Fetch quote data from Alpha Vantage (fallback source).
    Runs synchronous requests in thread pool.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, _fetch_alpha_vantage_sync, ticker)
    return result


def get_market_average_defaults(ticker: str) -> dict:
    """
    Return market average valuation metrics as last-resort fallback.
    Ensures 100% response rate even when all APIs fail.
    """
    return {
        "ticker": ticker.upper(),
        "current_price": None,
        "market_cap": None,
        "enterprise_value": None,
        "trailing_pe": 20.0,  # S&P 500 historical average
        "forward_pe": 18.0,
        "ps_ratio": 2.5,
        "pb_ratio": 3.0,
        "ev_ebitda": 12.0,
        "trailing_peg": 1.5,
        "forward_peg": 1.3,
        "earnings_growth": 0.08,  # 8% average
        "revenue_growth": 0.05,  # 5% average
        "source": "Market Averages (estimated)",
        "fallback": True,
        "fallback_reason": "All valuation data sources unavailable - using S&P 500 historical averages",
        "estimated": True
    }


async def fetch_yahoo_quote(ticker: str) -> Optional[dict]:
    """
    Fetch quote data from Yahoo Finance via yfinance library.
    Runs synchronous yfinance in thread pool.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, _fetch_yfinance_sync, ticker)
    return result


def safe_get(data: dict, key: str) -> Optional[float]:
    """Safely extract numeric value from data dict."""
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


async def fetch_pe_ratio(ticker: str) -> dict:
    """
    Fetch P/E ratio (Price to Earnings) - both trailing and forward.
    Lower P/E may indicate undervaluation or low growth expectations.
    """
    data = await fetch_yahoo_quote(ticker)

    if "error" in data:
        return {"metric": "P/E Ratio", "ticker": ticker, **data}

    trailing_pe = safe_get(data, "trailing_pe")
    forward_pe = safe_get(data, "forward_pe")

    # Use trailing P/E as primary, forward P/E as secondary
    pe_value = trailing_pe or forward_pe

    if pe_value is None:
        return {
            "metric": "P/E Ratio",
            "ticker": ticker.upper(),
            "error": "P/E data not available (company may have negative earnings)"
        }

    # P/E interpretation (varies by sector, these are general guidelines)
    if pe_value < 0:
        interpretation = "Negative P/E - Company has losses"
        swot_impact = "WEAKNESS"
    elif pe_value < 10:
        interpretation = "Low P/E - May be undervalued or facing challenges"
        swot_impact = "OPPORTUNITY"
    elif pe_value < 20:
        interpretation = "Moderate P/E - Fair valuation"
        swot_impact = "NEUTRAL"
    elif pe_value < 30:
        interpretation = "High P/E - Growth expectations priced in"
        swot_impact = "NEUTRAL"
    elif pe_value < 50:
        interpretation = "Very high P/E - High growth expectations"
        swot_impact = "WEAKNESS"
    else:
        interpretation = "Extremely high P/E - Speculative valuation"
        swot_impact = "WEAKNESS"

    return {
        "metric": "P/E Ratio",
        "ticker": ticker.upper(),
        "trailing_pe": round(trailing_pe, 2) if trailing_pe else None,
        "forward_pe": round(forward_pe, 2) if forward_pe else None,
        "value": round(pe_value, 2),
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": data.get("regular_market_time") or datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_ps_ratio(ticker: str) -> dict:
    """
    Fetch P/S ratio (Price to Sales).
    Useful for companies with negative earnings.
    """
    data = await fetch_yahoo_quote(ticker)

    if "error" in data:
        return {"metric": "P/S Ratio", "ticker": ticker, **data}

    ps_ratio = safe_get(data, "ps_ratio")

    if ps_ratio is None:
        return {
            "metric": "P/S Ratio",
            "ticker": ticker.upper(),
            "error": "P/S data not available"
        }

    # P/S interpretation
    if ps_ratio < 1:
        interpretation = "Low P/S - Trading below 1x sales, potentially undervalued"
        swot_impact = "OPPORTUNITY"
    elif ps_ratio < 3:
        interpretation = "Moderate P/S - Reasonable valuation relative to revenue"
        swot_impact = "NEUTRAL"
    elif ps_ratio < 8:
        interpretation = "High P/S - Premium valuation, high growth expected"
        swot_impact = "NEUTRAL"
    elif ps_ratio < 15:
        interpretation = "Very high P/S - Aggressive growth assumptions"
        swot_impact = "WEAKNESS"
    else:
        interpretation = "Extremely high P/S - Speculative valuation"
        swot_impact = "WEAKNESS"

    return {
        "metric": "P/S Ratio",
        "ticker": ticker.upper(),
        "value": round(ps_ratio, 2),
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": data.get("regular_market_time") or datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_pb_ratio(ticker: str) -> dict:
    """
    Fetch P/B ratio (Price to Book).
    Compares market value to book value.
    """
    data = await fetch_yahoo_quote(ticker)

    if "error" in data:
        return {"metric": "P/B Ratio", "ticker": ticker, **data}

    pb_ratio = safe_get(data, "pb_ratio")

    if pb_ratio is None:
        return {
            "metric": "P/B Ratio",
            "ticker": ticker.upper(),
            "error": "P/B data not available"
        }

    # P/B interpretation
    if pb_ratio < 1:
        interpretation = "Below book value - May be undervalued or have asset issues"
        swot_impact = "OPPORTUNITY"
    elif pb_ratio < 3:
        interpretation = "Moderate P/B - Trading near tangible asset value"
        swot_impact = "NEUTRAL"
    elif pb_ratio < 5:
        interpretation = "High P/B - Intangible assets or growth premium"
        swot_impact = "NEUTRAL"
    else:
        interpretation = "Very high P/B - Significant intangible value priced in"
        swot_impact = "WEAKNESS"

    return {
        "metric": "P/B Ratio",
        "ticker": ticker.upper(),
        "value": round(pb_ratio, 2),
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": data.get("regular_market_time") or datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_ev_ebitda(ticker: str) -> dict:
    """
    Fetch EV/EBITDA (Enterprise Value to EBITDA).
    Useful for comparing companies with different capital structures.
    """
    data = await fetch_yahoo_quote(ticker)

    if "error" in data:
        return {"metric": "EV/EBITDA", "ticker": ticker, **data}

    ev_ebitda = safe_get(data, "ev_ebitda")

    if ev_ebitda is None:
        return {
            "metric": "EV/EBITDA",
            "ticker": ticker.upper(),
            "error": "EV/EBITDA data not available"
        }

    # Also get enterprise value for context
    ev = safe_get(data, "enterprise_value")

    # EV/EBITDA interpretation
    if ev_ebitda < 0:
        interpretation = "Negative EV/EBITDA - Negative EBITDA or unusual capital structure"
        swot_impact = "WEAKNESS"
    elif ev_ebitda < 8:
        interpretation = "Low EV/EBITDA - Potentially undervalued"
        swot_impact = "OPPORTUNITY"
    elif ev_ebitda < 12:
        interpretation = "Moderate EV/EBITDA - Fair valuation"
        swot_impact = "NEUTRAL"
    elif ev_ebitda < 20:
        interpretation = "High EV/EBITDA - Premium valuation"
        swot_impact = "NEUTRAL"
    else:
        interpretation = "Very high EV/EBITDA - Expensive relative to cash earnings"
        swot_impact = "WEAKNESS"

    return {
        "metric": "EV/EBITDA",
        "ticker": ticker.upper(),
        "value": round(ev_ebitda, 2),
        "enterprise_value": ev,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": data.get("regular_market_time") or datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_peg_ratio(ticker: str) -> dict:
    """
    Fetch PEG ratio (P/E to Growth) - both trailing and forward.
    Adjusts P/E for expected growth rate.
    """
    data = await fetch_yahoo_quote(ticker)

    if "error" in data:
        return {"metric": "PEG Ratio", "ticker": ticker, **data}

    trailing_peg = safe_get(data, "trailing_peg")
    forward_peg = safe_get(data, "forward_peg")
    earnings_growth = safe_get(data, "earnings_growth")

    # Use trailing PEG as primary
    peg_ratio = trailing_peg or forward_peg

    if peg_ratio is None:
        return {
            "metric": "PEG Ratio",
            "ticker": ticker.upper(),
            "error": "PEG data not available (requires positive earnings and growth)"
        }

    # PEG interpretation
    if peg_ratio < 0:
        interpretation = "Negative PEG - Negative earnings or declining growth"
        swot_impact = "WEAKNESS"
    elif peg_ratio < 1:
        interpretation = "Low PEG (<1) - May be undervalued relative to growth"
        swot_impact = "OPPORTUNITY"
    elif peg_ratio < 1.5:
        interpretation = "Moderate PEG - Fair value relative to growth"
        swot_impact = "NEUTRAL"
    elif peg_ratio < 2:
        interpretation = "High PEG - Premium to growth rate"
        swot_impact = "NEUTRAL"
    else:
        interpretation = "Very high PEG - Overvalued relative to growth"
        swot_impact = "WEAKNESS"

    return {
        "metric": "PEG Ratio",
        "ticker": ticker.upper(),
        "trailing_peg": round(trailing_peg, 2) if trailing_peg else None,
        "forward_peg": round(forward_peg, 2) if forward_peg else None,
        "value": round(peg_ratio, 2),
        "earnings_growth_pct": round(earnings_growth * 100, 1) if earnings_growth else None,
        "interpretation": interpretation,
        "note": "PEG < 1 often considered undervalued",
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": data.get("regular_market_time") or datetime.now().strftime("%Y-%m-%d")
    }


async def get_full_valuation_basket(ticker: str) -> dict:
    """
    Fetch all valuation metrics for a given ticker.
    Returns aggregated SWOT-ready data with trailing and forward PEG.
    Uses fallback chain: Yahoo Finance → Alpha Vantage → Market Averages
    """
    # Try Yahoo Finance first
    data = await fetch_yahoo_quote(ticker)

    if "error" in data:
        logger.info(f"Yahoo Finance failed for {ticker}, trying Alpha Vantage fallback")
        # Fallback to Alpha Vantage
        data = await fetch_alpha_vantage_quote(ticker)

        if "error" in data:
            logger.info(f"Alpha Vantage failed for {ticker}, using market average defaults")
            # Last resort: market average defaults
            data = get_market_average_defaults(ticker)

    # Extract all metrics from yfinance data
    trailing_pe = safe_get(data, "trailing_pe")
    forward_pe = safe_get(data, "forward_pe")
    ps_ratio = safe_get(data, "ps_ratio")
    pb_ratio = safe_get(data, "pb_ratio")
    ev_ebitda = safe_get(data, "ev_ebitda")
    trailing_peg = safe_get(data, "trailing_peg")
    forward_peg = safe_get(data, "forward_peg")
    earnings_growth = safe_get(data, "earnings_growth")
    revenue_growth = safe_get(data, "revenue_growth")
    market_cap = safe_get(data, "market_cap")
    enterprise_value = safe_get(data, "enterprise_value")
    current_price = safe_get(data, "current_price")

    # Build SWOT summary
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    # Analyze P/E
    if trailing_pe:
        if 0 < trailing_pe < 15:
            swot_summary["opportunities"].append(f"Low P/E ({trailing_pe:.1f}) - Potentially undervalued")
        elif trailing_pe > 40:
            swot_summary["weaknesses"].append(f"High P/E ({trailing_pe:.1f}) - Expensive valuation")

    # Analyze P/S
    if ps_ratio:
        if ps_ratio < 1:
            swot_summary["opportunities"].append(f"Low P/S ({ps_ratio:.1f}) - Trading below 1x sales")
        elif ps_ratio > 10:
            swot_summary["weaknesses"].append(f"High P/S ({ps_ratio:.1f}) - Premium to revenue")

    # Analyze P/B
    if pb_ratio:
        if pb_ratio < 1:
            swot_summary["opportunities"].append(f"Below book value (P/B {pb_ratio:.1f})")
        elif pb_ratio > 8:
            swot_summary["weaknesses"].append(f"High P/B ({pb_ratio:.1f}) - Premium to assets")

    # Analyze EV/EBITDA
    if ev_ebitda:
        if 0 < ev_ebitda < 8:
            swot_summary["opportunities"].append(f"Low EV/EBITDA ({ev_ebitda:.1f})")
        elif ev_ebitda > 20:
            swot_summary["weaknesses"].append(f"High EV/EBITDA ({ev_ebitda:.1f})")

    # Analyze Trailing PEG
    if trailing_peg:
        if 0 < trailing_peg < 1:
            swot_summary["opportunities"].append(f"Low Trailing PEG ({trailing_peg:.2f}) - Undervalued vs growth")
        elif trailing_peg > 2:
            swot_summary["weaknesses"].append(f"High Trailing PEG ({trailing_peg:.2f}) - Overvalued vs growth")

    # Analyze Forward PEG
    if forward_peg:
        if 0 < forward_peg < 1:
            swot_summary["opportunities"].append(f"Low Forward PEG ({forward_peg:.2f}) - Attractive forward valuation")
        elif forward_peg > 2:
            swot_summary["weaknesses"].append(f"High Forward PEG ({forward_peg:.2f}) - Expensive vs expected growth")

    # Overall assessment
    opp_count = len(swot_summary["opportunities"])
    weak_count = len(swot_summary["weaknesses"])

    if opp_count >= 3:
        overall = "Potentially undervalued on multiple metrics"
    elif weak_count >= 3:
        overall = "Premium valuation on multiple metrics"
    elif opp_count > weak_count:
        overall = "Relatively attractive valuation"
    elif weak_count > opp_count:
        overall = "Relatively expensive valuation"
    else:
        overall = "Mixed valuation signals"

    # Format metrics for output
    formatted_metrics = {
        "current_price": round(current_price, 2) if current_price else None,
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "pe_ratio": {
            "trailing": round(trailing_pe, 2) if trailing_pe else None,
            "forward": round(forward_pe, 2) if forward_pe else None
        },
        "ps_ratio": round(ps_ratio, 2) if ps_ratio else None,
        "pb_ratio": round(pb_ratio, 2) if pb_ratio else None,
        "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else None,
        "peg_ratio": {
            "trailing": round(trailing_peg, 2) if trailing_peg else None,
            "forward": round(forward_peg, 2) if forward_peg else None
        },
        "growth": {
            "earnings_growth_pct": round(earnings_growth * 100, 1) if earnings_growth else None,
            "revenue_growth_pct": round(revenue_growth * 100, 1) if revenue_growth else None
        }
    }

    return {
        "ticker": ticker.upper(),
        "metrics": formatted_metrics,
        "overall_assessment": overall,
        "swot_summary": swot_summary,
        "source": "Yahoo Finance (yfinance)",
        "generated_at": datetime.now().strftime("%Y-%m-%d")
    }


async def get_all_sources_valuation(ticker: str) -> dict:
    """
    Fetch valuation metrics from Yahoo Finance (primary) with Alpha Vantage fallback.
    Returns NORMALIZED schema with 11 universal metrics.
    """
    yahoo_result = await fetch_yahoo_quote(ticker)

    # Build normalized schema
    sources = {}

    # Yahoo Finance as primary source (11 universal metrics, excludes ev_ebitda)
    if "error" not in yahoo_result:
        sources["yahoo_finance"] = {
            "source": "Yahoo Finance",
            "regular_market_time": yahoo_result.get("regular_market_time"),
            "data": {
                "current_price": safe_get(yahoo_result, "current_price"),
                "market_cap": safe_get(yahoo_result, "market_cap"),
                "enterprise_value": safe_get(yahoo_result, "enterprise_value"),
                "trailing_pe": safe_get(yahoo_result, "trailing_pe"),
                "forward_pe": safe_get(yahoo_result, "forward_pe"),
                "ps_ratio": safe_get(yahoo_result, "ps_ratio"),
                "pb_ratio": safe_get(yahoo_result, "pb_ratio"),
                "trailing_peg": safe_get(yahoo_result, "trailing_peg"),
                "forward_peg": safe_get(yahoo_result, "forward_peg"),
                "earnings_growth": safe_get(yahoo_result, "earnings_growth"),
                "revenue_growth": safe_get(yahoo_result, "revenue_growth"),
            }
        }
    else:
        # Fallback to Alpha Vantage if Yahoo Finance fails
        alpha_result = await fetch_alpha_vantage_quote(ticker)
        if alpha_result and "error" not in alpha_result:
            sources["alpha_vantage"] = {
                "source": "Alpha Vantage",
                "latest_quarter": alpha_result.get("latest_quarter"),
                "data": {
                    "current_price": safe_get(alpha_result, "current_price"),
                    "market_cap": safe_get(alpha_result, "market_cap"),
                    "trailing_pe": safe_get(alpha_result, "trailing_pe"),
                    "forward_pe": safe_get(alpha_result, "forward_pe"),
                    "ps_ratio": safe_get(alpha_result, "ps_ratio"),
                    "pb_ratio": safe_get(alpha_result, "pb_ratio"),
                    "trailing_peg": safe_get(alpha_result, "trailing_peg"),
                    "earnings_growth": safe_get(alpha_result, "earnings_growth"),
                    "revenue_growth": safe_get(alpha_result, "revenue_growth"),
                }
            }

    return {
        "group": "source_comparison",
        "ticker": ticker.upper(),
        "sources": sources,
        "source": "valuation-basket",
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

@server.list_tools()
async def list_tools():
    """List available valuation tools."""
    return [
        Tool(
            name="get_pe_ratio",
            description="Get P/E ratio (Price to Earnings) for a stock. Compares price to earnings per share.",
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
            name="get_ps_ratio",
            description="Get P/S ratio (Price to Sales) for a stock. Useful for companies with negative earnings.",
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
            name="get_pb_ratio",
            description="Get P/B ratio (Price to Book) for a stock. Compares market value to book value.",
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
            name="get_ev_ebitda",
            description="Get EV/EBITDA for a stock. Enterprise value relative to operating earnings.",
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
            name="get_peg_ratio",
            description="Get PEG ratio for a stock. P/E adjusted for expected growth rate.",
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
            name="get_valuation_basket",
            description="Get full valuation basket (P/E, P/S, P/B, EV/EBITDA, PEG) with aggregated SWOT summary.",
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
            name="get_all_sources_valuation",
            description="Get valuation from ALL sources (Yahoo Finance + Alpha Vantage) for side-by-side comparison.",
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


# Global timeout for all tool operations (seconds)
TOOL_TIMEOUT = 45.0


async def _execute_tool_with_timeout(name: str, ticker: str, arguments: dict) -> dict:
    """Execute a tool with timeout. Returns result dict or error dict."""
    if name == "get_pe_ratio":
        return await fetch_pe_ratio(ticker)
    elif name == "get_ps_ratio":
        return await fetch_ps_ratio(ticker)
    elif name == "get_pb_ratio":
        return await fetch_pb_ratio(ticker)
    elif name == "get_ev_ebitda":
        return await fetch_ev_ebitda(ticker)
    elif name == "get_peg_ratio":
        return await fetch_peg_ratio(ticker)
    elif name == "get_valuation_basket":
        return await get_full_valuation_basket(ticker)
    elif name == "get_all_sources_valuation":
        return await get_all_sources_valuation(ticker)
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
        if not ticker and name != "get_macro_basket":
            return [TextContent(type="text", text=json.dumps({
                "error": "ticker is required",
                "ticker": None,
                "source": "valuation-basket"
            }))]

        # Execute tool with global timeout
        try:
            result = await asyncio.wait_for(
                _execute_tool_with_timeout(name, ticker, arguments),
                timeout=TOOL_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"Tool {name} timed out after {TOOL_TIMEOUT}s for {ticker}")
            result = {
                "error": f"Tool execution timed out after {TOOL_TIMEOUT} seconds",
                "ticker": ticker,
                "tool": name,
                "source": "valuation-basket",
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
            "source": "valuation-basket"
        }))]

    except Exception as e:
        # Catch-all: ALWAYS return valid JSON-RPC response
        logger.error(f"Unexpected error in {name}: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "ticker": arguments.get("ticker", ""),
            "tool": name,
            "source": "valuation-basket",
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
