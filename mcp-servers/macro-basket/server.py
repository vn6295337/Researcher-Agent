"""
Macro Basket MCP Server

Economic environment indicators from FRED (Federal Reserve Economic Data).
Provides macroeconomic context for SWOT analysis:
- GDP Growth → Economic expansion/contraction
- Interest Rates → Cost of borrowing
- CPI / Inflation → Purchasing power erosion
- Unemployment → Labor market health

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
Free tier: Unlimited requests with API key (10 req/sec rate limit)
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
logger = logging.getLogger("macro-basket")

# Initialize MCP server
server = Server("macro-basket")

# FRED API configuration
FRED_API_KEY = os.getenv("FRED_API_KEY") or os.getenv("FRED_VIX_API_KEY")
FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# FRED Series IDs
FRED_SERIES = {
    "gdp_growth": "A191RL1Q225SBEA",  # Real GDP growth rate (quarterly, % change)
    "interest_rate": "FEDFUNDS",       # Federal Funds Effective Rate
    "cpi": "CPIAUCSL",                 # Consumer Price Index for All Urban Consumers
    "inflation_rate": "FPCPITOTLZGUSA", # Inflation rate (annual %)
    "unemployment": "UNRATE",          # Unemployment Rate
}


# ============================================================
# FRED DATA FETCHERS
# ============================================================

async def fetch_fred_series(series_id: str, limit: int = 12) -> Optional[dict]:
    """
    Fetch data from FRED API for a given series.

    Args:
        series_id: FRED series identifier
        limit: Number of observations to fetch
    """
    if not FRED_API_KEY:
        return {
            "error": "FRED_API_KEY not configured",
            "message": "Add FRED_API_KEY to ~/.env file. Get free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        }

    try:
        async with httpx.AsyncClient() as client:
            # Get series info
            info_url = f"{FRED_BASE_URL}/series"
            info_params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json"
            }
            info_resp = await client.get(info_url, params=info_params, timeout=10)
            info_data = info_resp.json()

            series_info = info_data.get("seriess", [{}])[0]

            # Get observations
            obs_url = f"{FRED_BASE_URL}/series/observations"
            obs_params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit
            }
            obs_resp = await client.get(obs_url, params=obs_params, timeout=10)
            obs_data = obs_resp.json()

            observations = obs_data.get("observations", [])

            # Get latest valid value
            latest_value = None
            latest_date = None
            for obs in observations:
                if obs.get("value") and obs["value"] != ".":
                    latest_value = float(obs["value"])
                    latest_date = obs["date"]
                    break

            # Get previous value for change calculation
            previous_value = None
            for obs in observations[1:]:
                if obs.get("value") and obs["value"] != ".":
                    previous_value = float(obs["value"])
                    break

            return {
                "series_id": series_id,
                "title": series_info.get("title", series_id),
                "units": series_info.get("units", ""),
                "frequency": series_info.get("frequency", ""),
                "latest_value": latest_value,
                "latest_date": latest_date,
                "previous_value": previous_value,
                "source": "FRED (Federal Reserve)"
            }

    except Exception as e:
        logger.error(f"FRED fetch error for {series_id}: {e}")
        return {"error": str(e), "series_id": series_id}


async def fetch_gdp_growth() -> dict:
    """
    Fetch GDP growth rate from FRED.
    Indicates economic expansion or contraction.
    """
    data = await fetch_fred_series(FRED_SERIES["gdp_growth"], limit=8)

    if "error" in data:
        return {"metric": "GDP Growth", **data}

    value = data["latest_value"]

    # GDP interpretation
    if value is None:
        interpretation = "Data unavailable"
        swot_impact = "NEUTRAL"
    elif value > 3:
        interpretation = "Strong economic growth - Favorable business environment"
        swot_impact = "OPPORTUNITY"
    elif value > 1:
        interpretation = "Moderate growth - Stable economic conditions"
        swot_impact = "NEUTRAL"
    elif value > 0:
        interpretation = "Slow growth - Cautious economic outlook"
        swot_impact = "THREAT"
    elif value > -2:
        interpretation = "Economic contraction - Recessionary conditions"
        swot_impact = "THREAT"
    else:
        interpretation = "Severe contraction - Deep recession"
        swot_impact = "SEVERE_THREAT"

    return {
        "metric": "GDP Growth",
        "value": round(value, 2) if value else None,
        "unit": "% change (quarterly, annualized)",
        "date": data["latest_date"],
        "previous_value": round(data["previous_value"], 2) if data["previous_value"] else None,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": datetime.now().isoformat()
    }


async def fetch_interest_rates() -> dict:
    """
    Fetch Federal Funds Rate from FRED.
    Indicates cost of borrowing and monetary policy stance.
    """
    data = await fetch_fred_series(FRED_SERIES["interest_rate"], limit=12)

    if "error" in data:
        return {"metric": "Interest Rate", **data}

    value = data["latest_value"]
    previous = data["previous_value"]

    # Interest rate interpretation
    if value is None:
        interpretation = "Data unavailable"
        swot_impact = "NEUTRAL"
        trend = "unknown"
    else:
        # Determine trend
        if previous and value > previous + 0.1:
            trend = "rising"
        elif previous and value < previous - 0.1:
            trend = "falling"
        else:
            trend = "stable"

        if value > 5:
            interpretation = f"High interest rates ({trend}) - Tight monetary policy, higher borrowing costs"
            swot_impact = "THREAT"
        elif value > 3:
            interpretation = f"Moderate rates ({trend}) - Balanced monetary policy"
            swot_impact = "NEUTRAL"
        elif value > 1:
            interpretation = f"Low rates ({trend}) - Accommodative policy, favorable for borrowing"
            swot_impact = "OPPORTUNITY"
        else:
            interpretation = f"Near-zero rates ({trend}) - Highly accommodative, may signal economic stress"
            swot_impact = "NEUTRAL"

    return {
        "metric": "Federal Funds Rate",
        "value": round(value, 2) if value else None,
        "unit": "%",
        "date": data["latest_date"],
        "previous_value": round(previous, 2) if previous else None,
        "trend": trend if value else None,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": datetime.now().isoformat()
    }


async def fetch_cpi() -> dict:
    """
    Fetch Consumer Price Index and calculate year-over-year inflation.
    """
    data = await fetch_fred_series(FRED_SERIES["cpi"], limit=13)  # Need 13 months for YoY

    if "error" in data:
        return {"metric": "CPI / Inflation", **data}

    # For CPI, we need to calculate YoY change
    # Fetch full series to calculate properly
    if not FRED_API_KEY:
        return {"metric": "CPI / Inflation", "error": "FRED_API_KEY required"}

    try:
        async with httpx.AsyncClient() as client:
            obs_url = f"{FRED_BASE_URL}/series/observations"
            obs_params = {
                "series_id": FRED_SERIES["cpi"],
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 13
            }
            obs_resp = await client.get(obs_url, params=obs_params, timeout=10)
            obs_data = obs_resp.json()

            observations = obs_data.get("observations", [])

            # Get current and year-ago values
            current_cpi = None
            current_date = None
            year_ago_cpi = None

            valid_obs = [(o["date"], float(o["value"])) for o in observations
                        if o.get("value") and o["value"] != "."]

            if len(valid_obs) >= 2:
                current_date, current_cpi = valid_obs[0]
                # Find observation ~12 months ago
                if len(valid_obs) >= 12:
                    _, year_ago_cpi = valid_obs[11]
                else:
                    _, year_ago_cpi = valid_obs[-1]

            if current_cpi and year_ago_cpi:
                yoy_inflation = ((current_cpi - year_ago_cpi) / year_ago_cpi) * 100
            else:
                yoy_inflation = None

    except Exception as e:
        logger.error(f"CPI calculation error: {e}")
        yoy_inflation = None
        current_date = None

    # Inflation interpretation
    if yoy_inflation is None:
        interpretation = "Data unavailable"
        swot_impact = "NEUTRAL"
    elif yoy_inflation > 6:
        interpretation = "High inflation - Eroding purchasing power, cost pressures"
        swot_impact = "THREAT"
    elif yoy_inflation > 4:
        interpretation = "Elevated inflation - Above target, potential rate hikes"
        swot_impact = "THREAT"
    elif yoy_inflation > 2:
        interpretation = "Moderate inflation - Near Fed target (2%)"
        swot_impact = "NEUTRAL"
    elif yoy_inflation > 0:
        interpretation = "Low inflation - Subdued price pressures"
        swot_impact = "OPPORTUNITY"
    else:
        interpretation = "Deflation - Falling prices, potential economic weakness"
        swot_impact = "THREAT"

    return {
        "metric": "CPI / Inflation",
        "value": round(yoy_inflation, 2) if yoy_inflation else None,
        "unit": "% YoY",
        "date": current_date,
        "fed_target": 2.0,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": "FRED (Federal Reserve)",
        "as_of": datetime.now().isoformat()
    }


async def fetch_unemployment() -> dict:
    """
    Fetch unemployment rate from FRED.
    Indicates labor market health.
    """
    data = await fetch_fred_series(FRED_SERIES["unemployment"], limit=12)

    if "error" in data:
        return {"metric": "Unemployment", **data}

    value = data["latest_value"]
    previous = data["previous_value"]

    # Unemployment interpretation
    if value is None:
        interpretation = "Data unavailable"
        swot_impact = "NEUTRAL"
        trend = "unknown"
    else:
        # Determine trend
        if previous and value > previous + 0.2:
            trend = "rising"
        elif previous and value < previous - 0.2:
            trend = "falling"
        else:
            trend = "stable"

        if value < 4:
            interpretation = f"Low unemployment ({trend}) - Tight labor market, wage pressures"
            swot_impact = "OPPORTUNITY" if trend != "rising" else "NEUTRAL"
        elif value < 5:
            interpretation = f"Normal unemployment ({trend}) - Healthy labor market"
            swot_impact = "NEUTRAL"
        elif value < 7:
            interpretation = f"Elevated unemployment ({trend}) - Labor market slack"
            swot_impact = "THREAT"
        else:
            interpretation = f"High unemployment ({trend}) - Weak labor market, recessionary"
            swot_impact = "SEVERE_THREAT"

    return {
        "metric": "Unemployment Rate",
        "value": round(value, 1) if value else None,
        "unit": "%",
        "date": data["latest_date"],
        "previous_value": round(previous, 1) if previous else None,
        "trend": trend if value else None,
        "interpretation": interpretation,
        "swot_category": swot_impact,
        "source": data["source"],
        "as_of": datetime.now().isoformat()
    }


async def get_full_macro_basket() -> dict:
    """
    Fetch all macro indicators with aggregated SWOT summary.
    """
    # Fetch all metrics concurrently
    gdp_task = fetch_gdp_growth()
    rates_task = fetch_interest_rates()
    cpi_task = fetch_cpi()
    unemployment_task = fetch_unemployment()

    gdp, rates, cpi, unemployment = await asyncio.gather(
        gdp_task, rates_task, cpi_task, unemployment_task
    )

    # Aggregate SWOT impacts
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    for metric in [gdp, rates, cpi, unemployment]:
        if "error" in metric:
            continue
        impact = metric.get("swot_category", "NEUTRAL")
        desc = f"{metric['metric']}: {metric.get('value', 'N/A')}{metric.get('unit', '')} - {metric.get('interpretation', '')}"

        if impact == "OPPORTUNITY":
            swot_summary["opportunities"].append(desc)
        elif impact in ["THREAT", "SEVERE_THREAT"]:
            swot_summary["threats"].append(desc)

    # Overall economic assessment
    threat_count = len(swot_summary["threats"])
    opp_count = len(swot_summary["opportunities"])

    if threat_count >= 3:
        overall = "Challenging macroeconomic environment"
    elif threat_count >= 2:
        overall = "Mixed macroeconomic conditions with headwinds"
    elif opp_count >= 2:
        overall = "Favorable macroeconomic environment"
    else:
        overall = "Neutral macroeconomic conditions"

    return {
        "basket": "Macro Indicators",
        "metrics": {
            "gdp_growth": gdp,
            "interest_rate": rates,
            "cpi_inflation": cpi,
            "unemployment": unemployment
        },
        "overall_assessment": overall,
        "swot_summary": swot_summary,
        "generated_at": datetime.now().isoformat()
    }


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

@server.list_tools()
async def list_tools():
    """List available macro tools."""
    return [
        Tool(
            name="get_gdp",
            description="Get real GDP growth rate. Indicates economic expansion or contraction.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_interest_rates",
            description="Get Federal Funds Rate. Indicates cost of borrowing and monetary policy stance.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_cpi",
            description="Get Consumer Price Index and year-over-year inflation rate.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_unemployment",
            description="Get unemployment rate. Indicates labor market health.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_macro_basket",
            description="Get full macro basket (GDP, Interest Rates, CPI, Unemployment) with aggregated SWOT summary.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool invocations."""
    try:
        if name == "get_gdp":
            result = await fetch_gdp_growth()
        elif name == "get_interest_rates":
            result = await fetch_interest_rates()
        elif name == "get_cpi":
            result = await fetch_cpi()
        elif name == "get_unemployment":
            result = await fetch_unemployment()
        elif name == "get_macro_basket":
            result = await get_full_macro_basket()
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
