"""
Volatility Basket Fetchers - Pure data fetching functions.

Separated from server.py to avoid MCP SDK import issues in aggregator.
"""

import asyncio
import logging
import os
import statistics
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import httpx

# Load environment variables
env_paths = [
    Path.home() / ".env",
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

logger = logging.getLogger("volatility-fetchers")

# API Keys
FRED_API_KEY = os.getenv("FRED_API_KEY") or os.getenv("FRED_VIX_API_KEY")

# Yahoo Finance headers
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


async def fetch_vix_from_fred() -> Optional[dict]:
    """Fetch VIX from FRED (authoritative source)."""
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

            for obs in observations:
                if obs.get("value") and obs["value"] != ".":
                    current_price = float(obs["value"])
                    break
            else:
                return None

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
    """Fetch VIX from Yahoo Finance (fallback)."""
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
    """Fetch VIX with fallback chain: FRED -> Yahoo."""
    vix_data = await fetch_vix_from_fred()
    if not vix_data:
        vix_data = await fetch_vix_from_yahoo()

    if not vix_data:
        return {"metric": "VIX", "error": "All sources failed"}

    current_price = vix_data["value"]
    previous_close = vix_data["previous_close"]

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
    """Calculate Beta coefficient from price data."""
    try:
        async with httpx.AsyncClient() as client:
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

            stock_closes = [c for c in stock_closes if c is not None]
            market_closes = [c for c in market_closes if c is not None]
            min_len = min(len(stock_closes), len(market_closes))
            stock_closes = stock_closes[-min_len:]
            market_closes = market_closes[-min_len:]

            if len(stock_closes) < 30:
                return {"metric": "Beta", "ticker": ticker, "error": "Insufficient data"}

            stock_returns = [(stock_closes[i] - stock_closes[i-1]) / stock_closes[i-1]
                            for i in range(1, len(stock_closes))]
            market_returns = [(market_closes[i] - market_closes[i-1]) / market_closes[i-1]
                             for i in range(1, len(market_closes))]

            n = len(stock_returns)
            mean_stock = sum(stock_returns) / n
            mean_market = sum(market_returns) / n

            covariance = sum((stock_returns[i] - mean_stock) * (market_returns[i] - mean_market)
                            for i in range(n)) / (n - 1)
            variance_market = sum((market_returns[i] - mean_market) ** 2
                                  for i in range(n)) / (n - 1)

            beta = covariance / variance_market if variance_market != 0 else 1.0

            if beta < 0.8:
                interpretation = "Low beta - Defensive stock"
                swot_impact = "STRENGTH"
            elif beta < 1.2:
                interpretation = "Market beta - Moves with market"
                swot_impact = "NEUTRAL"
            elif beta < 1.5:
                interpretation = "High beta - More volatile"
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
                "source": "Calculated from Yahoo Finance",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Beta fetch error for {ticker}: {e}")
        return {"metric": "Beta", "ticker": ticker, "error": str(e)}


async def fetch_historical_volatility(ticker: str, period_days: int = 30) -> dict:
    """Calculate historical volatility from price data."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {"interval": "1d", "range": "3mo"}
            response = await client.get(url, params=params, headers=YAHOO_HEADERS, timeout=10)
            data = response.json()

            result = data["chart"]["result"][0]
            closes = result["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None][-period_days:]

            if len(closes) < 10:
                return {"metric": "Historical Volatility", "ticker": ticker, "error": "Insufficient data"}

            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            daily_vol = statistics.stdev(returns)
            annual_vol = daily_vol * (252 ** 0.5) * 100

            if annual_vol < 20:
                interpretation = "Low volatility - Stable"
                swot_impact = "STRENGTH"
            elif annual_vol < 35:
                interpretation = "Moderate volatility - Normal"
                swot_impact = "NEUTRAL"
            elif annual_vol < 50:
                interpretation = "High volatility - Significant swings"
                swot_impact = "WEAKNESS"
            else:
                interpretation = "Very high volatility - Extreme"
                swot_impact = "WEAKNESS"

            return {
                "metric": "Historical Volatility",
                "ticker": ticker.upper(),
                "value": round(annual_vol, 2),
                "unit": "% annualized",
                "period_days": period_days,
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Calculated from Yahoo Finance",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Historical volatility error for {ticker}: {e}")
        return {"metric": "Historical Volatility", "ticker": ticker, "error": str(e)}


async def fetch_implied_volatility_proxy(ticker: str) -> dict:
    """Estimate implied volatility from options data."""
    try:
        async with httpx.AsyncClient() as client:
            quote_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            quote_resp = await client.get(quote_url, params={"interval": "1d", "range": "1d"}, headers=YAHOO_HEADERS, timeout=10)
            quote_data = quote_resp.json()
            current_price = quote_data["chart"]["result"][0]["meta"]["regularMarketPrice"]

            options_url = f"https://query1.finance.yahoo.com/v7/finance/options/{ticker}"
            options_resp = await client.get(options_url, headers=YAHOO_HEADERS, timeout=10)
            options_data = options_resp.json()

            if "optionChain" not in options_data or not options_data["optionChain"]["result"]:
                return {"metric": "Implied Volatility", "ticker": ticker, "error": "No options data"}

            result = options_data["optionChain"]["result"][0]
            calls = result.get("options", [{}])[0].get("calls", [])

            if not calls:
                return {"metric": "Implied Volatility", "ticker": ticker, "error": "No calls data"}

            atm_call = min(calls, key=lambda x: abs(x.get("strike", 0) - current_price))
            iv = atm_call.get("impliedVolatility", 0) * 100

            if iv < 25:
                interpretation = "Low IV - Limited movement expected"
                swot_impact = "OPPORTUNITY"
            elif iv < 40:
                interpretation = "Moderate IV - Normal expected movement"
                swot_impact = "NEUTRAL"
            elif iv < 60:
                interpretation = "High IV - Significant movement expected"
                swot_impact = "THREAT"
            else:
                interpretation = "Very high IV - Extreme movement expected"
                swot_impact = "THREAT"

            return {
                "metric": "Implied Volatility",
                "ticker": ticker.upper(),
                "value": round(iv, 2),
                "unit": "%",
                "strike": atm_call.get("strike"),
                "interpretation": interpretation,
                "swot_category": swot_impact,
                "source": "Yahoo Finance Options",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"IV fetch error for {ticker}: {e}")
        return {"metric": "Implied Volatility", "ticker": ticker, "error": str(e)}


async def get_full_volatility_basket(ticker: str) -> dict:
    """Fetch all volatility metrics for a ticker."""
    vix, beta, hv, iv = await asyncio.gather(
        fetch_vix(),
        fetch_beta(ticker),
        fetch_historical_volatility(ticker),
        fetch_implied_volatility_proxy(ticker)
    )

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
