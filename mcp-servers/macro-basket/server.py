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

# BEA API configuration (Primary for GDP)
# Get free key at: https://apps.bea.gov/api/signup/
BEA_API_KEY = os.getenv("BEA_API_KEY")
BEA_BASE_URL = "https://apps.bea.gov/api/data"

# BLS API configuration (Primary for CPI, Unemployment)
# v1 = no key needed (25 series/request), v2 = key for better limits
# Get free key at: https://data.bls.gov/registrationEngine/
BLS_API_KEY = os.getenv("BLS_API_KEY")  # Optional for v2
BLS_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SERIES = {
    "cpi": "CUUR0000SA0",        # CPI-U All items (same as FRED CPIAUCSL)
    "unemployment": "LNS14000000"  # Unemployment rate (same as FRED UNRATE)
}


# ============================================================
# FALLBACK DEFAULTS (Historical Averages)
# ============================================================

def get_default_gdp_growth() -> dict:
    """Return reasonable GDP growth default when FRED fails."""
    return {
        "metric": "GDP Growth",
        "value": 2.5,  # US long-term average ~2.5%
        "unit": "% change (quarterly, annualized)",
        "date": None,
        "previous_value": None,
        "interpretation": "Moderate growth - Stable economic conditions (estimated)",
        "swot_category": "NEUTRAL",
        "source": "Historical Average (estimated)",
        "fallback": True,
        "fallback_reason": "FRED API unavailable",
        "estimated": True,
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


def get_default_interest_rate() -> dict:
    """Return reasonable interest rate default when FRED fails."""
    return {
        "metric": "Federal Funds Rate",
        "value": 5.0,  # Recent elevated rates
        "unit": "%",
        "date": None,
        "previous_value": None,
        "trend": "stable",
        "interpretation": "High interest rates - Tight monetary policy (estimated)",
        "swot_category": "NEUTRAL",
        "source": "Historical Average (estimated)",
        "fallback": True,
        "fallback_reason": "FRED API unavailable",
        "estimated": True,
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


def get_default_cpi() -> dict:
    """Return reasonable CPI/inflation default when FRED fails."""
    return {
        "metric": "CPI / Inflation",
        "value": 3.0,  # Recent inflation rate
        "unit": "% YoY",
        "date": None,
        "fed_target": 2.0,
        "interpretation": "Moderate inflation - Near Fed target (estimated)",
        "swot_category": "NEUTRAL",
        "source": "Historical Average (estimated)",
        "fallback": True,
        "fallback_reason": "FRED API unavailable",
        "estimated": True,
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


def get_default_unemployment() -> dict:
    """Return reasonable unemployment default when FRED fails."""
    return {
        "metric": "Unemployment Rate",
        "value": 4.0,  # Near historical average
        "unit": "%",
        "date": None,
        "previous_value": None,
        "trend": "stable",
        "interpretation": "Low unemployment - Tight labor market (estimated)",
        "swot_category": "OPPORTUNITY",
        "source": "Historical Average (estimated)",
        "fallback": True,
        "fallback_reason": "FRED API unavailable",
        "estimated": True,
        "as_of": datetime.now().strftime("%Y-%m-%d")
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
    Uses fallback defaults if FRED unavailable.
    """
    data = await fetch_fred_series(FRED_SERIES["gdp_growth"], limit=8)

    if "error" in data:
        logger.info("FRED GDP fetch failed, using default values")
        return get_default_gdp_growth()

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
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_interest_rates() -> dict:
    """
    Fetch Federal Funds Rate from FRED.
    Indicates cost of borrowing and monetary policy stance.
    Uses fallback defaults if FRED unavailable.
    """
    data = await fetch_fred_series(FRED_SERIES["interest_rate"], limit=12)

    if "error" in data:
        logger.info("FRED interest rate fetch failed, using default values")
        return get_default_interest_rate()

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
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_cpi() -> dict:
    """
    Fetch Consumer Price Index and calculate year-over-year inflation.
    Uses fallback defaults if FRED unavailable.
    """
    data = await fetch_fred_series(FRED_SERIES["cpi"], limit=13)  # Need 13 months for YoY

    if "error" in data:
        logger.info("FRED CPI fetch failed, using default values")
        return get_default_cpi()

    # For CPI, we need to calculate YoY change
    # Fetch full series to calculate properly
    if not FRED_API_KEY:
        logger.info("FRED API key missing for CPI, using default values")
        return get_default_cpi()

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
        return get_default_cpi()

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
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


async def fetch_unemployment() -> dict:
    """
    Fetch unemployment rate from FRED.
    Indicates labor market health.
    Uses fallback defaults if FRED unavailable.
    """
    data = await fetch_fred_series(FRED_SERIES["unemployment"], limit=12)

    if "error" in data:
        logger.info("FRED unemployment fetch failed, using default values")
        return get_default_unemployment()

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
        "as_of": datetime.now().strftime("%Y-%m-%d")
    }


# ============================================================
# BEA DATA FETCHERS (Primary for GDP)
# ============================================================

async def fetch_bea_gdp() -> dict:
    """
    Fetch GDP growth rate from BEA NIPA dataset.
    Primary source - publishes before FRED syncs.

    API: https://apps.bea.gov/api/data/
    Dataset: NIPA, TableName: T10101 (GDP Percent Change)
    """
    if not BEA_API_KEY:
        return {
            "error": "BEA_API_KEY not configured",
            "message": "Add BEA_API_KEY to ~/.env file. Get free key at https://apps.bea.gov/api/signup/"
        }

    try:
        async with httpx.AsyncClient() as client:
            # Fetch GDP percent change from NIPA Table 1.1.1
            params = {
                "UserID": BEA_API_KEY,
                "method": "GetData",
                "datasetname": "NIPA",
                "TableName": "T10101",  # Percent Change From Preceding Period in Real GDP
                "Frequency": "Q",        # Quarterly
                "Year": "X",             # All recent years
                "ResultFormat": "JSON"
            }

            response = await client.get(BEA_BASE_URL, params=params, timeout=15)
            data = response.json()

            if "error" in str(data).lower():
                return {"error": f"BEA API error: {data}"}

            results = data.get("BEAAPI", {}).get("Results", {})
            data_rows = results.get("Data", [])

            if not data_rows:
                return {"error": "No GDP data returned from BEA"}

            # Find the most recent GDP growth rate (Line 1 = Real GDP)
            gdp_rows = [r for r in data_rows if r.get("LineNumber") == "1"]

            if not gdp_rows:
                return {"error": "No Real GDP data found in BEA response"}

            # Sort by TimePeriod (e.g., "2025Q3") descending
            gdp_rows.sort(key=lambda x: x.get("TimePeriod", ""), reverse=True)

            latest = gdp_rows[0]
            value = float(latest.get("DataValue", 0))
            time_period = latest.get("TimePeriod", "")  # e.g., "2025Q3"

            # Get previous quarter for comparison
            previous_value = None
            if len(gdp_rows) > 1:
                previous_value = float(gdp_rows[1].get("DataValue", 0))

            # GDP interpretation
            if value > 3:
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
                "value": round(value, 2),
                "unit": "% change (quarterly, annualized)",
                "date": time_period,
                "previous_value": round(previous_value, 2) if previous_value else None,
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "BEA (Bureau of Economic Analysis)",
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }

    except Exception as e:
        logger.error(f"BEA GDP fetch error: {e}")
        return {"error": str(e)}


# ============================================================
# BLS DATA FETCHERS (Primary for CPI, Unemployment)
# ============================================================

async def fetch_bls_series(series_ids: list, start_year: int = None, end_year: int = None) -> dict:
    """
    Fetch data from BLS API for given series.

    Args:
        series_ids: List of BLS series IDs
        start_year: Start year (default: current year - 2)
        end_year: End year (default: current year)
    """
    current_year = datetime.now().year
    if not start_year:
        start_year = current_year - 2
    if not end_year:
        end_year = current_year

    try:
        async with httpx.AsyncClient() as client:
            # BLS API requires POST with JSON payload
            payload = {
                "seriesid": series_ids,
                "startyear": str(start_year),
                "endyear": str(end_year)
            }

            # Add API key if available (for v2 with higher limits)
            if BLS_API_KEY:
                payload["registrationkey"] = BLS_API_KEY

            headers = {"Content-Type": "application/json"}
            response = await client.post(BLS_BASE_URL, json=payload, headers=headers, timeout=15)
            data = response.json()

            if data.get("status") != "REQUEST_SUCCEEDED":
                return {"error": f"BLS API error: {data.get('message', 'Unknown error')}"}

            return data

    except Exception as e:
        logger.error(f"BLS fetch error: {e}")
        return {"error": str(e)}


async def fetch_bls_cpi() -> dict:
    """
    Fetch CPI from BLS (primary source).
    Series: CUUR0000SA0 (CPI-U All items)
    """
    data = await fetch_bls_series([BLS_SERIES["cpi"]])

    if "error" in data:
        return data

    try:
        series_data = data.get("Results", {}).get("series", [])
        if not series_data:
            return {"error": "No CPI series data from BLS"}

        cpi_data = series_data[0].get("data", [])
        if not cpi_data:
            return {"error": "No CPI observations from BLS"}

        # BLS data is sorted newest first
        # Get current and year-ago values for YoY calculation
        current = cpi_data[0]
        current_value = float(current.get("value", 0))
        current_period = f"{current.get('year')}-{current.get('periodName', current.get('period', ''))}"

        # Find year-ago value (12 months back)
        year_ago_value = None
        for obs in cpi_data:
            if obs.get("year") == str(int(current.get("year")) - 1) and obs.get("period") == current.get("period"):
                year_ago_value = float(obs.get("value", 0))
                break

        # Calculate YoY inflation
        if year_ago_value and year_ago_value > 0:
            yoy_inflation = ((current_value - year_ago_value) / year_ago_value) * 100
        else:
            # Fallback: use monthly change annualized
            if len(cpi_data) > 1:
                prev_value = float(cpi_data[1].get("value", 0))
                if prev_value > 0:
                    monthly_change = (current_value - prev_value) / prev_value
                    yoy_inflation = monthly_change * 12 * 100
                else:
                    yoy_inflation = None
            else:
                yoy_inflation = None

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
            "date": current_period,
            "fed_target": 2.0,
            "interpretation": interpretation,
            "swot_category": swot_impact,
            "source": "BLS (Bureau of Labor Statistics)",
            "as_of": datetime.now().strftime("%Y-%m-%d")
        }

    except Exception as e:
        logger.error(f"BLS CPI processing error: {e}")
        return {"error": str(e)}


async def fetch_bls_unemployment() -> dict:
    """
    Fetch unemployment rate from BLS (primary source).
    Series: LNS14000000 (Unemployment rate)
    """
    data = await fetch_bls_series([BLS_SERIES["unemployment"]])

    if "error" in data:
        return data

    try:
        series_data = data.get("Results", {}).get("series", [])
        if not series_data:
            return {"error": "No unemployment series data from BLS"}

        unemp_data = series_data[0].get("data", [])
        if not unemp_data:
            return {"error": "No unemployment observations from BLS"}

        # BLS data is sorted newest first - filter out invalid values
        valid_data = [d for d in unemp_data if d.get("value") and d.get("value") != "-" and d.get("value") != "."]

        if not valid_data:
            return {"error": "No valid unemployment data from BLS"}

        current = valid_data[0]
        value = float(current.get("value", 0))
        current_period = f"{current.get('year')}-{current.get('periodName', current.get('period', ''))}"

        # Get previous value for trend
        previous_value = None
        if len(valid_data) > 1:
            previous_value = float(valid_data[1].get("value", 0))

        # Determine trend
        if previous_value:
            if value > previous_value + 0.2:
                trend = "rising"
            elif value < previous_value - 0.2:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        # Unemployment interpretation
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
            "value": round(value, 1),
            "unit": "%",
            "date": current_period,
            "previous_value": round(previous_value, 1) if previous_value else None,
            "trend": trend,
            "interpretation": interpretation,
            "swot_category": swot_impact,
            "source": "BLS (Bureau of Labor Statistics)",
            "as_of": datetime.now().strftime("%Y-%m-%d")
        }

    except Exception as e:
        logger.error(f"BLS unemployment processing error: {e}")
        return {"error": str(e)}


# ============================================================
# MULTI-SOURCE AGGREGATOR
# ============================================================

async def get_all_sources_macro() -> dict:
    """
    Fetch macro from ALL sources (BEA/BLS primary + FRED fallback) in parallel.
    Returns NORMALIZED schema for interpreted_metrics group.
    """
    # Fetch from all sources in parallel
    bea_gdp_task = fetch_bea_gdp()
    bls_cpi_task = fetch_bls_cpi()
    bls_unemp_task = fetch_bls_unemployment()
    fred_gdp_task = fetch_gdp_growth()
    fred_rates_task = fetch_interest_rates()
    fred_cpi_task = fetch_cpi()
    fred_unemp_task = fetch_unemployment()

    (bea_gdp, bls_cpi, bls_unemp,
     fred_gdp, fred_rates, fred_cpi, fred_unemp) = await asyncio.gather(
        bea_gdp_task, bls_cpi_task, bls_unemp_task,
        fred_gdp_task, fred_rates_task, fred_cpi_task, fred_unemp_task
    )

    # Use primary source, fallback to secondary if primary failed
    gdp = bea_gdp if "error" not in bea_gdp else fred_gdp
    cpi = bls_cpi if "error" not in bls_cpi else fred_cpi
    unemp = bls_unemp if "error" not in bls_unemp else fred_unemp
    rates = fred_rates  # FRED is primary for interest rates

    # Build normalized raw_metrics schema with temporal data
    return {
        "group": "raw_metrics",
        "ticker": "MACRO",
        "metrics": {
            "gdp_growth": {
                "value": gdp.get("value") if gdp else None,
                "data_type": "Quarterly",
                "as_of": gdp.get("date") if gdp else None,  # e.g., "2025Q3"
                "source": gdp.get("source") if gdp else None,
                "fallback": gdp.get("fallback", False) if gdp else True
            },
            "interest_rate": {
                "value": rates.get("value") if rates else None,
                "data_type": "Monthly",
                "as_of": rates.get("date") if rates else None,
                "source": rates.get("source") if rates else None,
                "fallback": rates.get("fallback", False) if rates else True
            },
            "cpi_inflation": {
                "value": cpi.get("value") if cpi else None,
                "data_type": "Monthly",
                "as_of": cpi.get("date") if cpi else None,
                "source": cpi.get("source") if cpi else None,
                "fallback": cpi.get("fallback", False) if cpi else True
            },
            "unemployment": {
                "value": unemp.get("value") if unemp else None,
                "data_type": "Monthly",
                "as_of": unemp.get("date") if unemp else None,
                "source": unemp.get("source") if unemp else None,
                "fallback": unemp.get("fallback", False) if unemp else True
            }
        },
        "source": "macro-basket",
        "as_of": datetime.now().strftime("%Y-%m-%d")
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
        "generated_at": datetime.now().strftime("%Y-%m-%d")
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
        ),
        Tool(
            name="get_all_sources_macro",
            description="Get macro from ALL sources (BEA/BLS primary + FRED fallback) for side-by-side comparison.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


# Global timeout for all tool operations (seconds)
TOOL_TIMEOUT = 45.0


async def _execute_tool_with_timeout(name: str, arguments: dict) -> dict:
    """Execute a tool with timeout. Returns result dict or error dict."""
    if name == "get_gdp":
        return await fetch_gdp_growth()
    elif name == "get_interest_rates":
        return await fetch_interest_rates()
    elif name == "get_cpi":
        return await fetch_cpi()
    elif name == "get_unemployment":
        return await fetch_unemployment()
    elif name == "get_macro_basket":
        return await get_full_macro_basket()
    elif name == "get_all_sources_macro":
        return await get_all_sources_macro()
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
            logger.error(f"Tool {name} timed out after {TOOL_TIMEOUT}s")
            result = {
                "error": f"Tool execution timed out after {TOOL_TIMEOUT} seconds",
                "tool": name,
                "source": "macro-basket",
                "fallback": True
            }

        # Ensure result is JSON serializable
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except json.JSONDecodeError as e:
        logger.error(f"JSON serialization error for {name}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"JSON serialization failed: {str(e)}",
            "tool": name,
            "source": "macro-basket"
        }))]

    except Exception as e:
        # Catch-all: ALWAYS return valid JSON-RPC response
        logger.error(f"Unexpected error in {name}: {type(e).__name__}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": f"{type(e).__name__}: {str(e)}",
            "tool": name,
            "source": "macro-basket",
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
