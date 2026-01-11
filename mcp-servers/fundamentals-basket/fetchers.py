"""
Financials Basket Fetchers - Pure data fetching functions.

Separated from server.py to avoid MCP SDK import issues in aggregator.
Falls back to Yahoo Finance when SEC EDGAR CIK is not found.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

import httpx
import yfinance as yf

logger = logging.getLogger("financials-fetchers")

# Thread pool for yfinance (synchronous library)
_executor = ThreadPoolExecutor(max_workers=2)

# SEC EDGAR requires User-Agent with contact info
SEC_HEADERS = {
    "User-Agent": "A2A-Strategy-Agent/1.0 (contact@example.com)",
    "Accept": "application/json",
}

# Cache for CIK lookups
CIK_CACHE = {}


def format_cik(cik: str) -> str:
    """Format CIK to 10 digits with leading zeros."""
    return str(cik).zfill(10)


async def ticker_to_cik(ticker: str) -> Optional[str]:
    """Convert ticker symbol to CIK number."""
    ticker = ticker.upper()

    if ticker in CIK_CACHE:
        return CIK_CACHE[ticker]

    try:
        async with httpx.AsyncClient() as client:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()

            for entry in data.values():
                if entry.get("ticker") == ticker:
                    cik = format_cik(entry.get("cik_str"))
                    CIK_CACHE[ticker] = cik
                    return cik

            return None
    except Exception as e:
        logger.error(f"CIK lookup error: {e}")
        return None


def get_latest_value(facts: dict, concept: str, unit: str = "USD") -> Optional[dict]:
    """Extract latest value for a concept from company facts."""
    try:
        concept_data = facts.get("us-gaap", {}).get(concept, {})
        units = concept_data.get("units", {}).get(unit, [])

        if not units:
            return None

        annual_facts = [f for f in units if f.get("form") == "10-K"]
        if not annual_facts:
            annual_facts = units

        annual_facts.sort(key=lambda x: x.get("end", ""), reverse=True)

        if annual_facts:
            latest = annual_facts[0]
            return {
                "value": latest.get("val"),
                "end_date": latest.get("end"),
                "fiscal_year": latest.get("fy"),
                "form": latest.get("form"),
                "filed": latest.get("filed"),
            }
        return None
    except Exception as e:
        logger.error(f"Error extracting {concept}: {e}")
        return None


def calculate_growth(facts: dict, concept: str, years: int = 3) -> Optional[float]:
    """Calculate CAGR for a concept over specified years."""
    try:
        concept_data = facts.get("us-gaap", {}).get(concept, {})
        units = concept_data.get("units", {}).get("USD", [])

        annual_facts = [f for f in units if f.get("form") == "10-K"]
        annual_facts.sort(key=lambda x: x.get("end", ""), reverse=True)

        if len(annual_facts) < years + 1:
            return None

        latest_val = annual_facts[0].get("val", 0)
        older_val = annual_facts[years].get("val", 0)

        if older_val <= 0 or latest_val <= 0:
            return None

        cagr = ((latest_val / older_val) ** (1 / years) - 1) * 100
        return round(cagr, 2)
    except Exception as e:
        logger.error(f"Growth calculation error: {e}")
        return None


# ============================================================
# SEC EDGAR FETCHERS
# ============================================================

async def fetch_financials_sec(ticker: str) -> dict:
    """Fetch key financial metrics from SEC EDGAR XBRL data."""
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=15)
            data = response.json()

            facts = data.get("facts", {})

            revenue = get_latest_value(facts, "RevenueFromContractWithCustomerExcludingAssessedTax") or \
                      get_latest_value(facts, "Revenues") or \
                      get_latest_value(facts, "SalesRevenueNet")

            net_income = get_latest_value(facts, "NetIncomeLoss")
            gross_profit = get_latest_value(facts, "GrossProfit")
            operating_income = get_latest_value(facts, "OperatingIncomeLoss")
            total_assets = get_latest_value(facts, "Assets")
            total_liabilities = get_latest_value(facts, "Liabilities")
            stockholders_equity = get_latest_value(facts, "StockholdersEquity")

            gross_margin = None
            if revenue and gross_profit and revenue["value"] and gross_profit["value"]:
                gross_margin = round((gross_profit["value"] / revenue["value"]) * 100, 2)

            operating_margin = None
            if revenue and operating_income and revenue["value"] and operating_income["value"]:
                operating_margin = round((operating_income["value"] / revenue["value"]) * 100, 2)

            net_margin = None
            if revenue and net_income and revenue["value"] and net_income["value"]:
                net_margin = round((net_income["value"] / revenue["value"]) * 100, 2)

            revenue_growth = calculate_growth(facts, "Revenues") or \
                            calculate_growth(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")

            return {
                "ticker": ticker.upper(),
                "revenue": revenue,
                "revenue_growth_3yr": revenue_growth,
                "net_income": net_income,
                "gross_profit": gross_profit,
                "operating_income": operating_income,
                "gross_margin_pct": gross_margin,
                "operating_margin_pct": operating_margin,
                "net_margin_pct": net_margin,
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "stockholders_equity": stockholders_equity,
                "source": "SEC EDGAR XBRL",
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }
    except Exception as e:
        logger.error(f"Financials error: {e}")
        return {"ticker": ticker, "error": str(e)}


async def fetch_debt_metrics_sec(ticker: str) -> dict:
    """Fetch debt and leverage metrics from SEC EDGAR."""
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=15)
            data = response.json()

            facts = data.get("facts", {})

            long_term_debt = get_latest_value(facts, "LongTermDebt") or \
                            get_latest_value(facts, "LongTermDebtNoncurrent")
            short_term_debt = get_latest_value(facts, "ShortTermBorrowings") or \
                             get_latest_value(facts, "DebtCurrent")
            total_debt = get_latest_value(facts, "DebtAndCapitalLeaseObligations") or \
                        get_latest_value(facts, "LongTermDebtAndCapitalLeaseObligations")
            cash = get_latest_value(facts, "CashAndCashEquivalentsAtCarryingValue") or \
                   get_latest_value(facts, "Cash")

            net_debt = None
            if total_debt and cash and total_debt.get("value") and cash.get("value"):
                net_debt = total_debt["value"] - cash["value"]
            elif long_term_debt and cash:
                ltd_val = long_term_debt.get("value", 0) or 0
                std_val = short_term_debt.get("value", 0) if short_term_debt else 0
                cash_val = cash.get("value", 0) or 0
                net_debt = ltd_val + std_val - cash_val

            stockholders_equity = get_latest_value(facts, "StockholdersEquity")
            debt_to_equity = None
            if total_debt and stockholders_equity:
                debt_val = total_debt.get("value", 0) or 0
                equity_val = stockholders_equity.get("value", 0) or 0
                if equity_val > 0:
                    debt_to_equity = round(debt_val / equity_val, 2)

            return {
                "ticker": ticker.upper(),
                "long_term_debt": long_term_debt,
                "short_term_debt": short_term_debt,
                "total_debt": total_debt,
                "cash": cash,
                "net_debt": {"value": net_debt} if net_debt else None,
                "debt_to_equity": debt_to_equity,
                "source": "SEC EDGAR XBRL",
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }
    except Exception as e:
        logger.error(f"Debt metrics error: {e}")
        return {"ticker": ticker, "error": str(e)}


async def fetch_cash_flow_sec(ticker: str) -> dict:
    """Fetch cash flow metrics from SEC EDGAR."""
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=15)
            data = response.json()

            facts = data.get("facts", {})

            operating_cf = get_latest_value(facts, "NetCashProvidedByUsedInOperatingActivities")
            capex = get_latest_value(facts, "PaymentsToAcquirePropertyPlantAndEquipment")

            fcf = None
            if operating_cf and capex:
                ocf_val = operating_cf.get("value", 0) or 0
                capex_val = capex.get("value", 0) or 0
                fcf = ocf_val - abs(capex_val)

            rd_expense = get_latest_value(facts, "ResearchAndDevelopmentExpense")

            return {
                "ticker": ticker.upper(),
                "operating_cash_flow": operating_cf,
                "capital_expenditure": capex,
                "free_cash_flow": {"value": fcf} if fcf else None,
                "rd_expense": rd_expense,
                "source": "SEC EDGAR XBRL",
                "as_of": datetime.now().strftime("%Y-%m-%d")
            }
    except Exception as e:
        logger.error(f"Cash flow error: {e}")
        return {"ticker": ticker, "error": str(e)}


# ============================================================
# YAHOO FINANCE FALLBACK
# ============================================================

def _fetch_yfinance_financials_sync(ticker: str) -> dict:
    """Synchronous yfinance fetch for financial data."""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        if not info or info.get("regularMarketPrice") is None:
            return {"error": f"No data found for ticker {ticker}"}

        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")
        gross_profit = info.get("grossProfits")
        operating_income = info.get("operatingIncome") or info.get("ebitda")
        total_cash = info.get("totalCash")
        total_debt = info.get("totalDebt")
        free_cash_flow = info.get("freeCashflow")
        operating_cash_flow = info.get("operatingCashflow")

        gross_margin = None
        if revenue and gross_profit and revenue > 0:
            gross_margin = round((gross_profit / revenue) * 100, 2)

        operating_margin = info.get("operatingMargins")
        if operating_margin:
            operating_margin = round(operating_margin * 100, 2)

        net_margin = info.get("profitMargins")
        if net_margin:
            net_margin = round(net_margin * 100, 2)

        revenue_growth = info.get("revenueGrowth")
        if revenue_growth:
            revenue_growth = round(revenue_growth * 100, 2)

        debt_to_equity = info.get("debtToEquity")
        if debt_to_equity:
            debt_to_equity = round(debt_to_equity / 100, 2)

        net_debt = None
        if total_debt is not None and total_cash is not None:
            net_debt = total_debt - total_cash

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "financials": {
                "revenue": {"value": revenue} if revenue else None,
                "net_income": {"value": net_income} if net_income else None,
                "gross_profit": {"value": gross_profit} if gross_profit else None,
                "operating_income": {"value": operating_income} if operating_income else None,
                "gross_margin_pct": gross_margin,
                "operating_margin_pct": operating_margin,
                "net_margin_pct": net_margin,
                "revenue_growth_3yr": revenue_growth,
            },
            "debt": {
                "total_debt": {"value": total_debt} if total_debt else None,
                "total_cash": {"value": total_cash} if total_cash else None,
                "net_debt": {"value": net_debt} if net_debt else None,
                "debt_to_equity": debt_to_equity,
            },
            "cash_flow": {
                "operating_cash_flow": {"value": operating_cash_flow} if operating_cash_flow else None,
                "free_cash_flow": {"value": free_cash_flow} if free_cash_flow else None,
            },
            "source": "Yahoo Finance (fallback)",
            "fallback": True,
            "fallback_reason": "CIK not found in SEC EDGAR",
            "as_of": datetime.now().strftime("%Y-%m-%d")
        }

    except Exception as e:
        logger.error(f"yfinance fallback error for {ticker}: {e}")
        return {"error": str(e), "fallback": True}


async def fetch_yfinance_fallback(ticker: str) -> dict:
    """Async wrapper for yfinance fallback."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_yfinance_financials_sync, ticker)


def _build_swot_from_fallback(data: dict) -> dict:
    """Build SWOT summary from Yahoo Finance fallback data."""
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    financials = data.get("financials", {})
    debt = data.get("debt", {})
    cash_flow = data.get("cash_flow", {})

    net_margin = financials.get("net_margin_pct")
    if net_margin is not None:
        if net_margin > 15:
            swot_summary["strengths"].append(f"High profitability: {net_margin}% net margin")
        elif net_margin > 5:
            swot_summary["strengths"].append(f"Healthy net margin: {net_margin}%")
        elif net_margin < 0:
            swot_summary["weaknesses"].append(f"Unprofitable: {net_margin}% net margin")
        elif net_margin < 5:
            swot_summary["weaknesses"].append(f"Thin margins: {net_margin}% net margin")

    op_margin = financials.get("operating_margin_pct")
    if op_margin is not None and op_margin > 20:
        swot_summary["strengths"].append(f"Strong operating efficiency: {op_margin}% operating margin")

    growth = financials.get("revenue_growth_3yr")
    if growth is not None:
        if growth > 15:
            swot_summary["strengths"].append(f"Strong revenue growth: {growth}%")
        elif growth > 5:
            swot_summary["strengths"].append(f"Positive revenue growth: {growth}%")
        elif growth < 0:
            swot_summary["weaknesses"].append(f"Declining revenue: {growth}%")

    d_to_e = debt.get("debt_to_equity")
    if d_to_e is not None:
        if d_to_e > 2:
            swot_summary["threats"].append(f"High leverage: {d_to_e}x debt-to-equity")
        elif d_to_e > 1:
            swot_summary["weaknesses"].append(f"Elevated debt: {d_to_e}x debt-to-equity")
        elif d_to_e < 0.5:
            swot_summary["strengths"].append(f"Low leverage: {d_to_e}x debt-to-equity")

    net_debt_data = debt.get("net_debt")
    if net_debt_data and net_debt_data.get("value"):
        net_debt_val = net_debt_data["value"]
        if net_debt_val < 0:
            swot_summary["strengths"].append("Net cash position (more cash than debt)")

    fcf_data = cash_flow.get("free_cash_flow")
    if fcf_data and fcf_data.get("value"):
        fcf_val = fcf_data["value"]
        if fcf_val > 0:
            swot_summary["strengths"].append(f"Positive free cash flow: ${fcf_val/1e9:.1f}B")
        else:
            swot_summary["weaknesses"].append(f"Negative free cash flow: ${fcf_val/1e9:.1f}B")

    return swot_summary


# ============================================================
# MAIN ENTRY POINT
# ============================================================

async def get_sec_fundamentals_basket(ticker: str) -> dict:
    """
    Get complete financials basket with SWOT interpretation.
    Falls back to Yahoo Finance if CIK is not found.
    """
    # First, check if CIK exists
    cik = await ticker_to_cik(ticker)

    if not cik:
        # Fallback to Yahoo Finance
        logger.info(f"CIK not found for {ticker}, using Yahoo Finance fallback")
        fallback_data = await fetch_yfinance_fallback(ticker)

        if "error" in fallback_data and not fallback_data.get("financials"):
            return {
                "ticker": ticker.upper(),
                "error": fallback_data.get("error"),
                "source": "Yahoo Finance (fallback)",
                "fallback": True,
                "fallback_reason": "CIK not found in SEC EDGAR"
            }

        # Build SWOT from fallback data
        swot_summary = _build_swot_from_fallback(fallback_data)
        fallback_data["swot_summary"] = swot_summary
        return fallback_data

    # Fetch from SEC EDGAR
    financials_task = fetch_financials_sec(ticker)
    debt_task = fetch_debt_metrics_sec(ticker)
    cashflow_task = fetch_cash_flow_sec(ticker)

    financials, debt, cashflow = await asyncio.gather(
        financials_task, debt_task, cashflow_task
    )

    # Build SWOT summary
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    if financials and "error" not in financials:
        growth = financials.get("revenue_growth_3yr")
        if growth is not None:
            if growth > 15:
                swot_summary["strengths"].append(f"Strong revenue growth: {growth}% CAGR (3yr)")
            elif growth > 5:
                swot_summary["strengths"].append(f"Positive revenue growth: {growth}% CAGR (3yr)")
            elif growth < 0:
                swot_summary["weaknesses"].append(f"Declining revenue: {growth}% CAGR (3yr)")

        net_margin = financials.get("net_margin_pct")
        if net_margin is not None:
            if net_margin > 15:
                swot_summary["strengths"].append(f"High profitability: {net_margin}% net margin")
            elif net_margin > 5:
                swot_summary["strengths"].append(f"Healthy net margin: {net_margin}%")
            elif net_margin < 0:
                swot_summary["weaknesses"].append(f"Unprofitable: {net_margin}% net margin")
            elif net_margin < 5:
                swot_summary["weaknesses"].append(f"Thin margins: {net_margin}% net margin")

        op_margin = financials.get("operating_margin_pct")
        if op_margin is not None and op_margin > 20:
            swot_summary["strengths"].append(f"Strong operating efficiency: {op_margin}% operating margin")

    if debt and "error" not in debt:
        d_to_e = debt.get("debt_to_equity")
        if d_to_e is not None:
            if d_to_e > 2:
                swot_summary["threats"].append(f"High leverage: {d_to_e}x debt-to-equity")
            elif d_to_e > 1:
                swot_summary["weaknesses"].append(f"Elevated debt: {d_to_e}x debt-to-equity")
            elif d_to_e < 0.5:
                swot_summary["strengths"].append(f"Low leverage: {d_to_e}x debt-to-equity")

        net_debt_data = debt.get("net_debt")
        if net_debt_data and net_debt_data.get("value"):
            net_debt_val = net_debt_data["value"]
            if net_debt_val < 0:
                swot_summary["strengths"].append("Net cash position (more cash than debt)")

    if cashflow and "error" not in cashflow:
        fcf_data = cashflow.get("free_cash_flow")
        if fcf_data and fcf_data.get("value"):
            fcf_val = fcf_data["value"]
            if fcf_val > 0:
                swot_summary["strengths"].append(f"Positive free cash flow: ${fcf_val/1e9:.1f}B")
            else:
                swot_summary["weaknesses"].append(f"Negative free cash flow: ${fcf_val/1e9:.1f}B")

        rd = cashflow.get("rd_expense")
        if rd and rd.get("value"):
            revenue = financials.get("revenue", {}).get("value") if financials else None
            if revenue and revenue > 0:
                rd_pct = (rd["value"] / revenue) * 100
                if rd_pct > 10:
                    swot_summary["opportunities"].append(f"High R&D investment: {rd_pct:.1f}% of revenue")

    return {
        "ticker": ticker.upper(),
        "financials": financials,
        "debt": debt,
        "cash_flow": cashflow,
        "swot_summary": swot_summary,
        "source": "SEC EDGAR",
        "generated_at": datetime.now().strftime("%Y-%m-%d")
    }
