"""
Financials Basket MCP Server

Fetches fundamental financial data from SEC EDGAR for SWOT analysis:
- Revenue, Net Income, Margins → Strengths/Weaknesses
- Debt levels, leverage ratios → Weaknesses/Threats
- R&D spend, CapEx → Opportunities
- Cash flow metrics → Strengths

API Documentation: https://www.sec.gov/edgar/sec-api-documentation
No API key required. Rate limit: 10 requests/second.
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
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("financials-basket")

# Thread pool for yfinance (synchronous library)
_executor = ThreadPoolExecutor(max_workers=2)

# Initialize MCP server
server = Server("financials-basket")

# SEC EDGAR requires User-Agent with contact info
SEC_HEADERS = {
    "User-Agent": "AI-Strategy-Copilot/1.0 (contact@example.com)",
    "Accept": "application/json",
}

# Cache for CIK lookups
CIK_CACHE = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_cik(cik: str) -> str:
    """Format CIK to 10 digits with leading zeros."""
    return str(cik).zfill(10)


async def ticker_to_cik(ticker: str) -> Optional[str]:
    """
    Convert ticker symbol to CIK number.
    Uses SEC's company tickers JSON.
    """
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
    """
    Extract latest value for a concept from company facts.
    Returns dict with value, period end date, and fiscal year.
    """
    # Defensive check for None or invalid facts
    if not facts or not isinstance(facts, dict):
        return None

    try:
        us_gaap = facts.get("us-gaap")
        if not us_gaap or not isinstance(us_gaap, dict):
            return None

        concept_data = us_gaap.get(concept)
        if not concept_data or not isinstance(concept_data, dict):
            return None

        units_data = concept_data.get("units")
        if not units_data or not isinstance(units_data, dict):
            return None

        units = units_data.get(unit, [])
        if not units or not isinstance(units, list):
            return None

        # Filter for annual (10-K) filings and get most recent
        annual_facts = [f for f in units if isinstance(f, dict) and f.get("form") == "10-K"]
        if not annual_facts:
            annual_facts = [f for f in units if isinstance(f, dict)]  # Fallback to all if no 10-K

        if not annual_facts:
            return None

        # Sort by end date descending
        annual_facts.sort(key=lambda x: x.get("end", ""), reverse=True)

        latest = annual_facts[0]
        return {
            "value": latest.get("val"),
            "end_date": latest.get("end"),
            "fiscal_year": latest.get("fy"),
            "form": latest.get("form")
        }
    except Exception as e:
        logger.error(f"Error extracting {concept}: {e}")
        return None


def calculate_growth(facts: dict, concept: str, years: int = 3) -> Optional[float]:
    """Calculate CAGR for a concept over specified years."""
    # Defensive check for None or invalid facts
    if not facts or not isinstance(facts, dict):
        return None

    try:
        us_gaap = facts.get("us-gaap")
        if not us_gaap or not isinstance(us_gaap, dict):
            return None

        concept_data = us_gaap.get(concept)
        if not concept_data or not isinstance(concept_data, dict):
            return None

        units_data = concept_data.get("units")
        if not units_data or not isinstance(units_data, dict):
            return None

        units = units_data.get("USD", [])
        if not units or not isinstance(units, list):
            return None

        annual_facts = [f for f in units if isinstance(f, dict) and f.get("form") == "10-K"]
        annual_facts.sort(key=lambda x: x.get("end", ""), reverse=True)

        if len(annual_facts) < years + 1:
            return None

        latest_val = annual_facts[0].get("val", 0) or 0
        older_val = annual_facts[years].get("val", 0) or 0

        if older_val <= 0 or latest_val <= 0:
            return None

        cagr = ((latest_val / older_val) ** (1 / years) - 1) * 100
        return round(cagr, 2)
    except Exception as e:
        logger.error(f"Growth calculation error: {e}")
        return None


# ============================================================
# DATA FETCHERS
# ============================================================

async def fetch_company_info(ticker: str) -> dict:
    """
    Fetch basic company information from SEC submissions.
    """
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()

            return {
                "ticker": ticker.upper(),
                "cik": cik,
                "name": data.get("name"),
                "sic": data.get("sic"),
                "sic_description": data.get("sicDescription"),
                "state": data.get("stateOfIncorporation"),
                "fiscal_year_end": data.get("fiscalYearEnd"),
                "source": "SEC EDGAR"
            }
    except Exception as e:
        logger.error(f"Company info error: {e}")
        return {"ticker": ticker, "error": str(e)}


async def fetch_financials(ticker: str) -> dict:
    """
    Fetch key financial metrics from SEC EDGAR XBRL data.
    """
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=15)
            data = response.json()

            facts = data.get("facts", {})

            # Extract key metrics
            revenue = get_latest_value(facts, "Revenues") or \
                      get_latest_value(facts, "RevenueFromContractWithCustomerExcludingAssessedTax") or \
                      get_latest_value(facts, "SalesRevenueNet")

            net_income = get_latest_value(facts, "NetIncomeLoss")

            gross_profit = get_latest_value(facts, "GrossProfit")

            operating_income = get_latest_value(facts, "OperatingIncomeLoss")

            total_assets = get_latest_value(facts, "Assets")

            total_liabilities = get_latest_value(facts, "Liabilities")

            stockholders_equity = get_latest_value(facts, "StockholdersEquity")

            # Calculate margins
            gross_margin = None
            if revenue and gross_profit and revenue["value"] and gross_profit["value"]:
                gross_margin = round((gross_profit["value"] / revenue["value"]) * 100, 2)

            operating_margin = None
            if revenue and operating_income and revenue["value"] and operating_income["value"]:
                operating_margin = round((operating_income["value"] / revenue["value"]) * 100, 2)

            net_margin = None
            if revenue and net_income and revenue["value"] and net_income["value"]:
                net_margin = round((net_income["value"] / revenue["value"]) * 100, 2)

            # Revenue growth
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
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Financials error: {e}")
        return {"ticker": ticker, "error": str(e)}


async def fetch_debt_metrics(ticker: str) -> dict:
    """
    Fetch debt and leverage metrics.
    """
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=15)
            data = response.json()

            facts = data.get("facts", {})

            # Debt metrics
            long_term_debt = get_latest_value(facts, "LongTermDebt") or \
                            get_latest_value(facts, "LongTermDebtNoncurrent")

            short_term_debt = get_latest_value(facts, "ShortTermBorrowings") or \
                             get_latest_value(facts, "DebtCurrent")

            total_debt = get_latest_value(facts, "DebtAndCapitalLeaseObligations") or \
                        get_latest_value(facts, "LongTermDebtAndCapitalLeaseObligations")

            cash = get_latest_value(facts, "CashAndCashEquivalentsAtCarryingValue") or \
                   get_latest_value(facts, "Cash")

            # Calculate net debt
            net_debt = None
            if total_debt and cash and total_debt.get("value") and cash.get("value"):
                net_debt = total_debt["value"] - cash["value"]
            elif long_term_debt and cash:
                ltd_val = long_term_debt.get("value", 0) or 0
                std_val = short_term_debt.get("value", 0) if short_term_debt else 0
                cash_val = cash.get("value", 0) or 0
                net_debt = ltd_val + std_val - cash_val

            # Get EBITDA or operating income for leverage ratio
            operating_income = get_latest_value(facts, "OperatingIncomeLoss")

            # Debt to equity
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
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Debt metrics error: {e}")
        return {"ticker": ticker, "error": str(e)}


async def fetch_cash_flow(ticker: str) -> dict:
    """
    Fetch cash flow metrics.
    """
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

            # Free Cash Flow = Operating CF - CapEx
            fcf = None
            if operating_cf and capex:
                ocf_val = operating_cf.get("value", 0) or 0
                capex_val = capex.get("value", 0) or 0
                fcf = ocf_val - abs(capex_val)  # CapEx is typically negative

            rd_expense = get_latest_value(facts, "ResearchAndDevelopmentExpense")

            return {
                "ticker": ticker.upper(),
                "operating_cash_flow": operating_cf,
                "capital_expenditure": capex,
                "free_cash_flow": {"value": fcf} if fcf else None,
                "rd_expense": rd_expense,
                "source": "SEC EDGAR XBRL",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Cash flow error: {e}")
        return {"ticker": ticker, "error": str(e)}


# 8-K Item Code Descriptions
ITEM_8K_CODES = {
    "1.01": "Entry into Material Definitive Agreement",
    "1.02": "Termination of Material Definitive Agreement",
    "1.03": "Bankruptcy or Receivership",
    "1.04": "Mine Safety",
    "2.01": "Completion of Acquisition or Disposition of Assets",
    "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of Direct Financial Obligation",
    "2.04": "Triggering Events (Accelerate/Increase Obligation)",
    "2.05": "Exit or Disposal Activities",
    "2.06": "Material Impairments",
    "3.01": "Delisting or Listing Standard Failure",
    "3.02": "Unregistered Sales of Equity Securities",
    "3.03": "Material Modification to Security Holder Rights",
    "4.01": "Changes in Certifying Accountant",
    "4.02": "Non-Reliance on Previously Issued Financials",
    "5.01": "Changes in Control of Registrant",
    "5.02": "Departure/Election of Directors or Officers",
    "5.03": "Amendments to Articles/Bylaws",
    "5.05": "Amendments to Code of Ethics",
    "5.06": "Change in Shell Company Status",
    "5.07": "Submission of Matters to Shareholder Vote",
    "5.08": "Shareholder Nominations",
    "6.01": "ABS Servicer Information",
    "6.02": "Change of ABS Servicer",
    "6.03": "Change in Credit Enhancement",
    "6.04": "Failure to Make Distribution",
    "6.05": "ABS Informational and Computational Material",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Events",
    "9.01": "Financial Statements and Exhibits",
}

# High-priority 8-K items (material risk events)
HIGH_PRIORITY_ITEMS = {
    "1.03",  # Bankruptcy
    "2.04",  # Triggering events
    "2.06",  # Material impairments
    "3.01",  # Delisting
    "4.02",  # Non-reliance on financials
    "5.01",  # Change in control
    "5.02",  # Executive departure
}


async def fetch_material_events(ticker: str, limit: int = 20) -> dict:
    """
    Fetch recent 8-K material events for a company.
    Returns filings with item codes and SWOT categorization.
    """
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()

            # Get recent filings
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            items_list = recent.get("items", [])
            descriptions = recent.get("primaryDocument", [])

            # Filter for 8-K filings
            events = []
            high_priority_events = []

            for i, form in enumerate(forms):
                if form == "8-K" and len(events) < limit:
                    item_codes = items_list[i] if i < len(items_list) else ""

                    # Parse item codes (comma-separated)
                    parsed_items = []
                    is_high_priority = False

                    if item_codes:
                        for code in item_codes.split(","):
                            code = code.strip()
                            if code in ITEM_8K_CODES:
                                parsed_items.append({
                                    "code": code,
                                    "description": ITEM_8K_CODES[code],
                                    "high_priority": code in HIGH_PRIORITY_ITEMS
                                })
                                if code in HIGH_PRIORITY_ITEMS:
                                    is_high_priority = True

                    event = {
                        "filing_date": dates[i] if i < len(dates) else None,
                        "accession_number": accessions[i] if i < len(accessions) else None,
                        "items": parsed_items,
                        "raw_items": item_codes,
                        "document": descriptions[i] if i < len(descriptions) else None,
                        "high_priority": is_high_priority,
                        "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&dateb=&owner=include&count=40"
                    }

                    events.append(event)
                    if is_high_priority:
                        high_priority_events.append(event)

            # SWOT categorization
            swot_implications = {
                "weaknesses": [],
                "threats": []
            }

            for event in high_priority_events[:5]:  # Top 5 high-priority
                for item in event.get("items", []):
                    code = item.get("code")
                    desc = item.get("description")
                    date = event.get("filing_date")

                    if code == "1.03":
                        swot_implications["threats"].append(f"Bankruptcy filing ({date})")
                    elif code == "2.06":
                        swot_implications["weaknesses"].append(f"Material impairment ({date})")
                    elif code == "3.01":
                        swot_implications["threats"].append(f"Delisting/listing issue ({date})")
                    elif code == "4.02":
                        swot_implications["threats"].append(f"Financial restatement risk ({date})")
                    elif code == "5.01":
                        swot_implications["weaknesses"].append(f"Change in control ({date})")
                    elif code == "5.02":
                        swot_implications["weaknesses"].append(f"Executive/director change ({date})")
                    elif code == "2.04":
                        swot_implications["threats"].append(f"Debt obligation triggered ({date})")

            return {
                "ticker": ticker.upper(),
                "cik": cik,
                "total_8k_filings": len([f for f in forms if f == "8-K"]),
                "recent_events": events,
                "high_priority_count": len(high_priority_events),
                "high_priority_events": high_priority_events[:5],
                "swot_implications": swot_implications,
                "source": "SEC EDGAR",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Material events error: {e}")
        return {"ticker": ticker, "error": str(e)}


# Going concern keywords to search in 10-K filings
GOING_CONCERN_KEYWORDS = [
    "going concern",
    "substantial doubt",
    "ability to continue",
    "continue as a going concern",
    "raise substantial doubt",
    "conditions that raise",
    "material uncertainty",
    "liquidity concerns",
]


async def fetch_going_concern(ticker: str) -> dict:
    """
    Fetch latest 10-K and search for going concern language.
    Returns matches with surrounding context.
    """
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            # Get submissions to find latest 10-K
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            dates = recent.get("filingDate", [])
            primary_docs = recent.get("primaryDocument", [])

            # Find latest 10-K
            filing_info = None
            for i, form in enumerate(forms):
                if form == "10-K":
                    filing_info = {
                        "form": form,
                        "accession": accessions[i].replace("-", ""),
                        "accession_formatted": accessions[i],
                        "date": dates[i],
                        "document": primary_docs[i] if i < len(primary_docs) else None
                    }
                    break

            if not filing_info:
                return {
                    "ticker": ticker.upper(),
                    "going_concern_found": False,
                    "message": "No 10-K filing found",
                    "source": "SEC EDGAR"
                }

            # Fetch the 10-K document
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{filing_info['accession']}/{filing_info['document']}"

            doc_response = await client.get(doc_url, headers=SEC_HEADERS, timeout=30)

            if doc_response.status_code != 200:
                return {
                    "ticker": ticker.upper(),
                    "going_concern_found": False,
                    "message": f"Could not fetch 10-K document (status {doc_response.status_code})",
                    "filing_date": filing_info["date"],
                    "source": "SEC EDGAR"
                }

            # Get text content (handle HTML)
            content = doc_response.text.lower()

            # Remove HTML tags for cleaner search
            import re
            text_content = re.sub(r'<[^>]+>', ' ', content)
            text_content = re.sub(r'\s+', ' ', text_content)

            # Search for keywords
            matches = []
            for keyword in GOING_CONCERN_KEYWORDS:
                if keyword in text_content:
                    # Find context around the keyword
                    idx = text_content.find(keyword)
                    start = max(0, idx - 150)
                    end = min(len(text_content), idx + len(keyword) + 150)
                    context = text_content[start:end].strip()

                    # Count occurrences
                    count = text_content.count(keyword)

                    matches.append({
                        "keyword": keyword,
                        "count": count,
                        "sample_context": f"...{context}..."
                    })

            # Determine risk level
            has_going_concern = len(matches) > 0
            risk_level = "none"
            if has_going_concern:
                total_mentions = sum(m["count"] for m in matches)
                if any(kw in ["substantial doubt", "raise substantial doubt"] for kw in [m["keyword"] for m in matches]):
                    risk_level = "high"
                elif total_mentions > 5:
                    risk_level = "medium"
                else:
                    risk_level = "low"

            # SWOT implications
            swot_implications = {"threats": []}
            if risk_level == "high":
                swot_implications["threats"].append(f"Going concern warning in 10-K ({filing_info['date']})")
            elif risk_level == "medium":
                swot_implications["threats"].append(f"Multiple going concern mentions in 10-K ({filing_info['date']})")

            return {
                "ticker": ticker.upper(),
                "going_concern_found": has_going_concern,
                "risk_level": risk_level,
                "filing_date": filing_info["date"],
                "filing_url": doc_url,
                "keyword_matches": matches,
                "swot_implications": swot_implications,
                "source": "SEC EDGAR 10-K",
                "as_of": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Going concern error: {e}")
        return {"ticker": ticker, "error": str(e)}


async def fetch_ownership_filings(ticker: str, limit: int = 20) -> dict:
    """
    Fetch ownership-related filings: 13D/13G (5%+ ownership), Form 4 (insider trades), 13F mentions.
    """
    cik = await ticker_to_cik(ticker)
    if not cik:
        return {"error": f"Could not find CIK for ticker {ticker}"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])

            # Ownership form types
            ownership_forms = {
                "SC 13D": "Beneficial ownership >5% (activist/intent to influence)",
                "SC 13D/A": "Amendment to 13D",
                "SC 13G": "Beneficial ownership >5% (passive investor)",
                "SC 13G/A": "Amendment to 13G",
                "4": "Insider transaction (officer/director/10%+ owner)",
                "4/A": "Amendment to Form 4",
                "3": "Initial insider ownership statement",
                "5": "Annual insider ownership changes",
            }

            filings_13d_13g = []
            filings_form4 = []

            for i, form in enumerate(forms):
                if form in ownership_forms:
                    filing = {
                        "form": form,
                        "description": ownership_forms[form],
                        "filing_date": dates[i] if i < len(dates) else None,
                        "accession_number": accessions[i] if i < len(accessions) else None,
                        "document": primary_docs[i] if i < len(primary_docs) else None,
                    }

                    if form.startswith("SC 13"):
                        if len(filings_13d_13g) < limit:
                            filings_13d_13g.append(filing)
                    elif form in ("3", "4", "4/A", "5"):
                        if len(filings_form4) < limit:
                            filings_form4.append(filing)

            # SWOT implications
            swot_implications = {
                "opportunities": [],
                "threats": []
            }

            # Recent 13D filings suggest activist interest
            recent_13d = [f for f in filings_13d_13g if f["form"] in ("SC 13D", "SC 13D/A")][:3]
            if recent_13d:
                dates_str = ", ".join([f["filing_date"] for f in recent_13d if f["filing_date"]])
                swot_implications["opportunities"].append(f"Activist investor interest (13D filings: {dates_str})")

            # Heavy insider selling could be a warning
            recent_form4 = filings_form4[:10]
            # Note: Would need to parse Form 4 XML to determine buy vs sell

            return {
                "ticker": ticker.upper(),
                "cik": cik,
                "ownership_filings": {
                    "13d_13g": filings_13d_13g[:limit],
                    "13d_13g_count": len([f for f in forms if f.startswith("SC 13")]),
                    "form4_insider": filings_form4[:limit],
                    "form4_count": len([f for f in forms if f in ("3", "4", "4/A", "5")]),
                },
                "swot_implications": swot_implications,
                "source": "SEC EDGAR",
                "as_of": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Ownership filings error: {e}")
        return {"ticker": ticker, "error": str(e)}


# ============================================================
# YAHOO FINANCE FALLBACK (when CIK not found)
# ============================================================

def _fetch_yfinance_financials_sync(ticker: str) -> dict:
    """
    Synchronous yfinance fetch for financial data.
    Used as fallback when SEC EDGAR CIK is not available.
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        if not info or info.get("regularMarketPrice") is None:
            return {"error": f"No data found for ticker {ticker}"}

        # Extract financial metrics from yfinance info
        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")
        gross_profit = info.get("grossProfits")
        operating_income = info.get("operatingIncome") or info.get("ebitda")
        total_assets = info.get("totalAssets")
        total_liabilities = info.get("totalDebt")
        stockholders_equity = info.get("bookValue")
        total_cash = info.get("totalCash")
        total_debt = info.get("totalDebt")
        free_cash_flow = info.get("freeCashflow")
        operating_cash_flow = info.get("operatingCashflow")

        # Calculate margins
        gross_margin = None
        if revenue and gross_profit and revenue > 0:
            gross_margin = round((gross_profit / revenue) * 100, 2)

        operating_margin = info.get("operatingMargins")
        if operating_margin:
            operating_margin = round(operating_margin * 100, 2)

        net_margin = info.get("profitMargins")
        if net_margin:
            net_margin = round(net_margin * 100, 2)

        # Revenue growth
        revenue_growth = info.get("revenueGrowth")
        if revenue_growth:
            revenue_growth = round(revenue_growth * 100, 2)

        # Debt to equity
        debt_to_equity = info.get("debtToEquity")
        if debt_to_equity:
            debt_to_equity = round(debt_to_equity / 100, 2)  # yfinance returns as percentage

        # Net debt
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
                "net_margin": net_margin,
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
            "as_of": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"yfinance fallback error for {ticker}: {e}")
        return {"error": str(e), "fallback": True}


async def fetch_yfinance_fallback(ticker: str) -> dict:
    """
    Async wrapper for yfinance fallback.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_yfinance_financials_sync, ticker)


def _build_swot_from_fallback(data: dict) -> dict:
    """
    Build SWOT summary from Yahoo Finance fallback data.
    """
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    financials = data.get("financials", {})
    debt = data.get("debt", {})
    cash_flow = data.get("cash_flow", {})

    # Analyze margins
    net_margin = financials.get("net_margin")
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

    # Revenue growth
    growth = financials.get("revenue_growth_3yr")
    if growth is not None:
        if growth > 15:
            swot_summary["strengths"].append(f"Strong revenue growth: {growth}%")
        elif growth > 5:
            swot_summary["strengths"].append(f"Positive revenue growth: {growth}%")
        elif growth < 0:
            swot_summary["weaknesses"].append(f"Declining revenue: {growth}%")

    # Debt analysis
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

    # Cash flow
    fcf_data = cash_flow.get("free_cash_flow")
    if fcf_data and fcf_data.get("value"):
        fcf_val = fcf_data["value"]
        if fcf_val > 0:
            swot_summary["strengths"].append(f"Positive free cash flow: ${fcf_val/1e9:.1f}B")
        else:
            swot_summary["weaknesses"].append(f"Negative free cash flow: ${fcf_val/1e9:.1f}B")

    return swot_summary


async def get_sec_fundamentals_basket(ticker: str) -> dict:
    """
    Get complete SEC fundamentals basket with SWOT interpretation.
    Falls back to Yahoo Finance if CIK is not found.
    """
    # First, check if CIK exists
    cik = await ticker_to_cik(ticker)

    if not cik:
        # Fallback to Yahoo Finance
        logger.info(f"CIK not found for {ticker}, using Yahoo Finance fallback")
        fallback_data = await fetch_yfinance_fallback(ticker)

        if "error" in fallback_data:
            return {
                "ticker": ticker.upper(),
                "error": fallback_data["error"],
                "source": "Yahoo Finance (fallback)",
                "fallback": True,
                "fallback_reason": "CIK not found in SEC EDGAR"
            }

        # Build SWOT from fallback data
        swot_summary = _build_swot_from_fallback(fallback_data)
        fallback_data["swot_summary"] = swot_summary
        return fallback_data

    # Fetch all data concurrently from SEC EDGAR
    company_task = fetch_company_info(ticker)
    financials_task = fetch_financials(ticker)
    debt_task = fetch_debt_metrics(ticker)
    cashflow_task = fetch_cash_flow(ticker)

    company, financials, debt, cashflow = await asyncio.gather(
        company_task, financials_task, debt_task, cashflow_task
    )

    # Build SWOT summary
    swot_summary = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    # Analyze financials for SWOT
    if financials and "error" not in financials:
        # Revenue growth
        growth = financials.get("revenue_growth_3yr")
        if growth is not None:
            if growth > 15:
                swot_summary["strengths"].append(f"Strong revenue growth: {growth}% CAGR (3yr)")
            elif growth > 5:
                swot_summary["strengths"].append(f"Positive revenue growth: {growth}% CAGR (3yr)")
            elif growth < 0:
                swot_summary["weaknesses"].append(f"Declining revenue: {growth}% CAGR (3yr)")

        # Margins
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

    # Analyze debt for SWOT
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

    # Analyze cash flow for SWOT
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
        "company": company,
        "financials": financials,
        "debt": debt,
        "cash_flow": cashflow,
        "swot_summary": swot_summary,
        "generated_at": datetime.now().isoformat()
    }


# ============================================================
# MCP TOOL DEFINITIONS
# ============================================================

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
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool invocations."""
    try:
        ticker = arguments.get("ticker", "").upper()
        if not ticker and name != "list_tools":
            return [TextContent(type="text", text="Error: ticker is required")]

        if name == "get_company_info":
            result = await fetch_company_info(ticker)
        elif name == "get_financials":
            result = await fetch_financials(ticker)
        elif name == "get_debt_metrics":
            result = await fetch_debt_metrics(ticker)
        elif name == "get_cash_flow":
            result = await fetch_cash_flow(ticker)
        elif name == "get_sec_fundamentals":
            result = await get_sec_fundamentals_basket(ticker)
        elif name == "get_material_events":
            limit = arguments.get("limit", 20)
            result = await fetch_material_events(ticker, limit)
        elif name == "get_ownership_filings":
            limit = arguments.get("limit", 20)
            result = await fetch_ownership_filings(ticker, limit)
        elif name == "get_going_concern":
            result = await fetch_going_concern(ticker)
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
