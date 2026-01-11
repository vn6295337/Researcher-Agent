#!/usr/bin/env python3
"""
Test script for SEC EDGAR fetchers (standalone, no MCP required).
Usage: python test_fetchers.py AAPL
"""

import asyncio
import sys
import os
from pathlib import Path

# Load .env from home directory
from dotenv import load_dotenv
env_path = Path.home() / ".env"
if env_path.exists():
    load_dotenv(env_path)

import httpx

# SEC EDGAR headers
SEC_HEADERS = {
    "User-Agent": "A2A-Strategy-Agent/1.0 (contact@example.com)",
    "Accept": "application/json",
}


def format_cik(cik: str) -> str:
    return str(cik).zfill(10)


async def ticker_to_cik(ticker: str) -> str:
    """Convert ticker to CIK."""
    async with httpx.AsyncClient() as client:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = await client.get(url, headers=SEC_HEADERS, timeout=10)
        data = response.json()

        for entry in data.values():
            if entry.get("ticker") == ticker.upper():
                return format_cik(entry.get("cik_str"))
        return None


def get_latest_value(facts: dict, concept: str, unit: str = "USD"):
    """Extract latest value for a concept."""
    try:
        concept_data = facts.get("us-gaap", {}).get(concept, {})
        units = concept_data.get("units", {}).get(unit, [])
        if not units:
            return None
        annual = [f for f in units if f.get("form") == "10-K"]
        if not annual:
            annual = units
        annual.sort(key=lambda x: x.get("end", ""), reverse=True)
        if annual:
            return annual[0].get("val")
        return None
    except:
        return None


async def test_all(ticker: str):
    """Test SEC EDGAR fetchers."""
    print(f"\n{'='*60}")
    print(f"SEC EDGAR Test for: {ticker}")
    print(f"{'='*60}\n")

    # 1. CIK Lookup
    print("1. Looking up CIK...")
    cik = await ticker_to_cik(ticker)
    if not cik:
        print(f"   Error: Could not find CIK for {ticker}")
        return
    print(f"   CIK: {cik}")

    # 2. Company Info
    print(f"\n2. Fetching company info...")
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()
            print(f"   Name: {data.get('name')}")
            print(f"   Industry: {data.get('sicDescription')}")
            print(f"   State: {data.get('stateOfIncorporation')}")
    except Exception as e:
        print(f"   Error: {e}")

    # 3. Financial Facts
    print(f"\n3. Fetching financial facts...")
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=15)
            data = response.json()
            facts = data.get("facts", {})

            revenue = get_latest_value(facts, "Revenues") or \
                     get_latest_value(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")
            net_income = get_latest_value(facts, "NetIncomeLoss")
            assets = get_latest_value(facts, "Assets")
            debt = get_latest_value(facts, "LongTermDebt")
            cash = get_latest_value(facts, "CashAndCashEquivalentsAtCarryingValue")

            print(f"   Revenue: ${revenue/1e9:.2f}B" if revenue else "   Revenue: N/A")
            print(f"   Net Income: ${net_income/1e9:.2f}B" if net_income else "   Net Income: N/A")
            print(f"   Total Assets: ${assets/1e9:.2f}B" if assets else "   Total Assets: N/A")
            print(f"   Long-term Debt: ${debt/1e9:.2f}B" if debt else "   Long-term Debt: N/A")
            print(f"   Cash: ${cash/1e9:.2f}B" if cash else "   Cash: N/A")

            if revenue and net_income:
                margin = (net_income / revenue) * 100
                print(f"   Net Margin: {margin:.1f}%")

    except Exception as e:
        print(f"   Error: {e}")

    # 4. Material Events (8-K filings)
    print(f"\n4. Fetching recent 8-K material events...")
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            items = recent.get("items", [])

            # High-priority item codes
            high_priority = {"1.03", "2.04", "2.06", "3.01", "4.02", "5.01", "5.02"}

            print(f"   Recent 8-K filings (last 10):")
            count = 0
            for i, form in enumerate(forms):
                if form == "8-K" and count < 10:
                    item_codes = items[i] if i < len(items) else ""
                    date = dates[i] if i < len(dates) else "N/A"
                    is_priority = any(code.strip() in high_priority for code in item_codes.split(",")) if item_codes else False
                    priority_flag = " ⚠️ HIGH PRIORITY" if is_priority else ""
                    print(f"   - {date}: {item_codes or 'No items'}{priority_flag}")
                    count += 1

    except Exception as e:
        print(f"   Error: {e}")

    # 5. Ownership Filings (13D/13G, Form 4)
    print(f"\n5. Fetching ownership filings...")
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = await client.get(url, headers=SEC_HEADERS, timeout=10)
            data = response.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])

            ownership_forms = {"SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A", "3", "4", "4/A", "5"}

            print(f"   Recent ownership filings (last 10):")
            count = 0
            for i, form in enumerate(forms):
                if form in ownership_forms and count < 10:
                    date = dates[i] if i < len(dates) else "N/A"
                    form_type = "13D/G" if form.startswith("SC 13") else "Insider"
                    print(f"   - {date}: {form} ({form_type})")
                    count += 1

            if count == 0:
                print("   No recent ownership filings found")

    except Exception as e:
        print(f"   Error: {e}")

    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    asyncio.run(test_all(ticker))
