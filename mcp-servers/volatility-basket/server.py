"""
Volatility Basket MCP Server

Aggregates volatility metrics from multiple free sources for SWOT analysis:
- VIX Index (CBOE) → External Threat indicator
- Beta (Yahoo Finance) → Internal Strength/Weakness
- Implied Volatility (derived) → Upcoming Threat/Opportunity
- Historical Volatility (calculated) → Operational Weakness

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
from typing import Optional
import statistics

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("volatility-basket")

# Initialize MCP server
server = Server("volatility-basket")

# API Keys (optional - enables authoritative sources)
FRED_API_KEY = os.getenv("FRED_API_KEY") or os.getenv("FRED_VIX_API_KEY")  # Get free key: https://fred.stlouisfed.org/docs/api/api_key.html
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")  # Get free key: https://www.alphavantage.co/support/#api-key

# Yahoo Finance requires browser-like headers
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# DATA FETCHERS
# ============================================================

async def fetch_vix_from_fred() -> Optional[dict]:
    """
    Fetch VIX from FRED (Federal Reserve Economic Data).
    Primary/authoritative source. Requires free API key.
    """
    if not FRED_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": "VIXCLS",
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 5
            }
            response = await client.get(url, params=params, timeout=10)
            data = response.json()

            observations = data.get("observations", [])
            if not observations:
                return None

            # Get latest non-null value
            for obs in observations:
                if obs.get("value") and obs["value"] != ".":
                    current_price = float(obs["value"])
                    break
            else:
                return None

            # Get previous for change calculation
            previous_close = current_price
            if len(observations) > 1 and observations[1].get("value") != ".":
                previous_close = float(observations[1]["value"])

            return {
                "value": current_price,
                "previous_close": previous_close,
                "source": "FRED (Federal Reserve)",
                "date": observations[0].get("date")
            }
    except Exception as e:
        logger.error(f"FRED VIX fetch error: {e}")
        return None


async def fetch_vix_from_yahoo() -> Optional[dict]:
    """
    Fetch VIX from Yahoo Finance (fallback source).
    """
    try:
        async with httpx.AsyncClient() as client:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
            params = {"interval": "1d", "range": "5d"}
            response = await client.get(url, params=params, headers=YAHOO_HEADERS, timeout=10)
            data = response.json()

            result = data["chart"]["result"][0]
            meta = result["meta"]
            current_price = meta.get("regularMarketPrice", 0)
            previous_close = meta.get("previousClose", current_price)

            return {
                "value": current_price,
                "previous_close": previous_close,
                "source": "Yahoo Finance"
            }
    except Exception as e:
        logger.error(f"Yahoo VIX fetch error: {e}")
        return None


async def fetch_vix() -> dict:
    """
    Fetch VIX index with fallback chain: FRED → Yahoo Finance.
    Returns current VIX level and interpretation.
    """
    # Try FRED first (authoritative), fallback to Yahoo
    vix_data = await fetch_vix_from_fred()
    if not vix_data:
        vix_data = await fetch_vix_from_yahoo()

    if not vix_data:
        return {"metric": "VIX", "error": "All sources failed"}

    current_price = vix_data["value"]
    previous_close = vix_data["previous_close"]

    # VIX interpretation thresholds
    if current_price < 15:
        interpretation = "Low volatility - Complacent market"
        swot_impact = "OPPORTUNITY"
    elif current_price < 20:
        interpretation = "Normal volatility - Stable conditions"
        swot_impact = "NEUTRAL"
    elif current_price < 30:
        interpretation = "Elevated volatility - Increased uncertainty"
        swot_impact = "THREAT"
    else:
        interpretation = "High volatility - Fear/crisis mode"
        swot_impact = "SEVERE_THREAT"

    return {
        "metric": "VIX",
        "value": round(current_price, 2),
        "previous_close": round(previous_close, 2),
        "change_pct": round((current_price - previous_close) / previous_close * 100, 2) if previous_close else 0,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": vix_data["source"],
        "as_of": datetime.now().isoformat()
    }


async def fetch_beta(ticker: str) -> dict:
    """
    Calculate Beta coefficient from price data.
    Beta = Covariance(stock, market) / Variance(market)
    Uses S&P 500 (^GSPC) as market benchmark.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Fetch stock and market data in parallel
            stock_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            market_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
            params = {"interval": "1d", "range": "1y"}

            stock_resp, market_resp = await asyncio.gather(
                client.get(stock_url, params=params, headers=YAHOO_HEADERS, timeout=10),
                client.get(market_url, params=params, headers=YAHOO_HEADERS, timeout=10)
            )

            stock_data = stock_resp.json()["chart"]["result"][0]
            market_data = market_resp.json()["chart"]["result"][0]

            stock_closes = stock_data["indicators"]["quote"][0]["close"]
            market_closes = market_data["indicators"]["quote"][0]["close"]

            # Filter None values and align lengths
            stock_closes = [c for c in stock_closes if c is not None]
            market_closes = [c for c in market_closes if c is not None]
            min_len = min(len(stock_closes), len(market_closes))
            stock_closes = stock_closes[-min_len:]
            market_closes = market_closes[-min_len:]

            if len(stock_closes) < 30:
                return {"metric": "Beta", "ticker": ticker, "error": "Insufficient data"}

            # Calculate daily returns
            stock_returns = [(stock_closes[i] - stock_closes[i-1]) / stock_closes[i-1]
                            for i in range(1, len(stock_closes))]
            market_returns = [(market_closes[i] - market_closes[i-1]) / market_closes[i-1]
                             for i in range(1, len(market_closes))]

            # Calculate Beta = Cov(stock, market) / Var(market)
            n = len(stock_returns)
            mean_stock = sum(stock_returns) / n
            mean_market = sum(market_returns) / n

            covariance = sum((stock_returns[i] - mean_stock) * (market_returns[i] - mean_market)
                            for i in range(n)) / (n - 1)
            variance_market = sum((market_returns[i] - mean_market) ** 2
                                  for i in range(n)) / (n - 1)

            beta = covariance / variance_market if variance_market != 0 else 1.0

            # Beta interpretation
            if beta < 0.8:
                interpretation = "Low beta - Defensive stock, less volatile than market"
                swot_impact = "STRENGTH"
            elif beta < 1.2:
                interpretation = "Market beta - Moves with the market"
                swot_impact = "NEUTRAL"
            elif beta < 1.5:
                interpretation = "High beta - More volatile than market"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very high beta - Significantly more volatile"
                swot_impact = "WEAKNESS"

            return {
                "metric": "Beta",
                "ticker": ticker.upper(),
                "value": round(beta, 3),
                "benchmark": "S&P 500",
                "period": "1 year",
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Calculated from Yahoo Finance data",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Beta fetch error for {ticker}: {e}")
        return {"metric": "Beta", "ticker": ticker, "error": str(e)}


async def fetch_historical_volatility(ticker: str, period_days: int = 30) -> dict:
    """
    Calculate historical volatility from price data.
    Uses standard deviation of daily returns annualized.
    """
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {"interval": "1d", "range": "3mo"}
            response = await client.get(url, params=params, headers=YAHOO_HEADERS, timeout=10)
            data = response.json()

            result = data["chart"]["result"][0]
            closes = result["indicators"]["quote"][0]["close"]

            # Filter None values and get recent period
            closes = [c for c in closes if c is not None][-period_days:]

            if len(closes) < 10:
                return {"metric": "Historical Volatility", "ticker": ticker, "error": "Insufficient data"}

            # Calculate daily returns
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

            # Calculate standard deviation and annualize (252 trading days)
            daily_vol = statistics.stdev(returns)
            annual_vol = daily_vol * (252 ** 0.5) * 100  # As percentage

            # Interpretation
            if annual_vol < 20:
                interpretation = "Low historical volatility - Stable price action"
                swot_impact = "STRENGTH"
            elif annual_vol < 35:
                interpretation = "Moderate volatility - Normal for equities"
                swot_impact = "NEUTRAL"
            elif annual_vol < 50:
                interpretation = "High volatility - Significant price swings"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very high volatility - Extreme price movements"
                swot_impact = "WEAKNESS"

            return {
                "metric": "Historical Volatility",
                "ticker": ticker.upper(),
                "value": round(annual_vol, 2),
                "unit": "% annualized",
                "period_days": period_days,
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Calculated from Yahoo Finance data",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Historical volatility error for {ticker}: {e}")
        return {"metric": "Historical Volatility", "ticker": ticker, "error": str(e)}


async def fetch_implied_volatility_proxy(ticker: str) -> dict:
    """
    Estimate implied volatility using options data from Yahoo Finance.
    Uses ATM options IV as proxy.
    """
    try:
        async with httpx.AsyncClient() as client:
            # First get current price
            quote_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            quote_resp = await client.get(quote_url, params={"interval": "1d", "range": "1d"}, headers=YAHOO_HEADERS, timeout=10)
            quote_data = quote_resp.json()
            current_price = quote_data["chart"]["result"][0]["meta"]["regularMarketPrice"]

            # Get options chain
            options_url = f"https://query1.finance.yahoo.com/v7/finance/options/{ticker}"
            options_resp = await client.get(options_url, headers=YAHOO_HEADERS, timeout=10)
            options_data = options_resp.json()

            if "optionChain" not in options_data or not options_data["optionChain"]["result"]:
                return {"metric": "Implied Volatility", "ticker": ticker, "error": "No options data"}

            result = options_data["optionChain"]["result"][0]
            calls = result.get("options", [{}])[0].get("calls", [])

            if not calls:
                return {"metric": "Implied Volatility", "ticker": ticker, "error": "No calls data"}

            # Find ATM option (closest to current price)
            atm_call = min(calls, key=lambda x: abs(x.get("strike", 0) - current_price))
            iv = atm_call.get("impliedVolatility", 0) * 100  # Convert to percentage

            # Interpretation
            if iv < 25:
                interpretation = "Low IV - Market expects limited price movement"
                swot_impact = "OPPORTUNITY"
            elif iv < 40:
                interpretation = "Moderate IV - Normal expected movement"
                swot_impact = "NEUTRAL"
            elif iv < 60:
                interpretation = "High IV - Market expects significant movement"
                swot_impact = "THREAT"
            else:
                interpretation = "Very high IV - Extreme movement expected (earnings, event)"
                swot_impact = "THREAT"

            return {
                "metric": "Implied Volatility",
                "ticker": ticker.upper(),
                "value": round(iv, 2),
                "unit": "%",
                "strike": atm_call.get("strike"),
                "expiration": result.get("expirationDates", [None])[0],
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Yahoo Finance Options",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"IV fetch error for {ticker}: {e}")
        return {"metric": "Implied Volatility", "ticker": ticker, "error": str(e)}


async def get_full_volatility_basket(ticker: str) -> dict:
    """
    Fetch all volatility metrics for a given ticker.
    Returns aggregated SWOT-ready data.
    """
    # Fetch all metrics concurrently
    vix_task = fetch_vix()
    beta_task = fetch_beta(ticker)
    hv_task = fetch_historical_volatility(ticker)
    iv_task = fetch_implied_volatility_proxy(ticker)

    vix, beta, hv, iv = await asyncio.gather(vix_task, beta_task, hv_task, iv_task)

    # Aggregate SWOT impacts
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    for metric in [vix, beta, hv, iv]:
        if "error" in metric:
            continue
        impact = metric.get("swot_category", "NEUTRAL")
        desc = f"{metric['metric']}: {metric.get('value', 'N/A')} - {metric.get('interpretation', '')}"

        if impact == "STRENGTH":
            swot_summary["strengths"].append(desc)
        elif impact == "WEAKNESS":
            swot_summary["weaknesses"].append(desc)
        elif impact == "OPPORTUNITY":
            swot_summary["opportunities"].append(desc)
        elif impact in ["THREAT", "SEVERE_THREAT"]:
            swot_summary["threats"].append(desc)

    return {
        "ticker": ticker.upper(),
        "metrics": {
            "vix": vix,
            "beta": beta,
            "historical_volatility": hv,
            "implied_volatility": iv
        },
        "swot_summary": swot_summary,
        "generated_at": datetime.now().isoformat()
    }


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

@server.list_tools()
async def list_tools():
    """List available volatility tools."""
    return [
        Tool(
            name="get_vix",
            description="Get current VIX (CBOE Volatility Index) level with SWOT interpretation. Indicates market-wide fear/greed.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_beta",
            description="Get Beta coefficient for a stock ticker. Measures volatility relative to market (S&P 500).",
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
            name="get_historical_volatility",
            description="Calculate historical volatility (annualized) from past price movements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "period_days": {
                        "type": "integer",
                        "description": "Number of days to calculate volatility over (default: 30)",
                        "default": 30
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_implied_volatility",
            description="Get implied volatility from options market. Indicates expected future price movement.",
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
            name="get_volatility_basket",
            description="Get full volatility basket (VIX, Beta, HV, IV) with aggregated SWOT summary for a ticker.",
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


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool invocations."""
    try:
        if name == "get_vix":
            result = await fetch_vix()
        elif name == "get_beta":
            ticker = arguments.get("ticker", "").upper()
            if not ticker:
                return [TextContent(type="text", text="Error: ticker is required")]
            result = await fetch_beta(ticker)
        elif name == "get_historical_volatility":
            ticker = arguments.get("ticker", "").upper()
            period = arguments.get("period_days", 30)
            if not ticker:
                return [TextContent(type="text", text="Error: ticker is required")]
            result = await fetch_historical_volatility(ticker, period)
        elif name == "get_implied_volatility":
            ticker = arguments.get("ticker", "").upper()
            if not ticker:
                return [TextContent(type="text", text="Error: ticker is required")]
            result = await fetch_implied_volatility_proxy(ticker)
        elif name == "get_volatility_basket":
            ticker = arguments.get("ticker", "").upper()
            if not ticker:
                return [TextContent(type="text", text="Error: ticker is required")]
            result = await get_full_volatility_basket(ticker)
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
