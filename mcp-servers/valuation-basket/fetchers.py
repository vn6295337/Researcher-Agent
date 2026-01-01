"""
Valuation Basket Fetchers - Pure data fetching functions.

Separated from server.py to avoid MCP SDK import issues in aggregator.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

logger = logging.getLogger("valuation-fetchers")

# Thread pool for running yfinance (synchronous)
executor = ThreadPoolExecutor(max_workers=2)


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
            "source": "Yahoo Finance (yfinance)"
        }

    except Exception as e:
        logger.error(f"yfinance fetch error for {ticker}: {e}")
        return {"error": str(e)}


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


async def get_full_valuation_basket(ticker: str) -> dict:
    """
    Fetch all valuation metrics for a given ticker.
    Returns aggregated SWOT-ready data with trailing and forward PEG.
    """
    # Fetch data once (to avoid multiple API calls)
    data = await fetch_yahoo_quote(ticker)

    if "error" in data:
        return {
            "ticker": ticker.upper(),
            "error": data["error"]
        }

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
        "generated_at": datetime.now().isoformat()
    }
