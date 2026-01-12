"""
E2E test for all 6 MCP servers using subprocess+MCP protocol (same as production).

Usage: python tests/test_mcp_e2e.py [TICKER] [COMPANY_NAME]
Default: KO "The Coca-Cola Company"
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from project .env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Import MCP client (subprocess+MCP protocol)
from mcp_client import call_mcp_server

# Default test company
DEFAULT_TICKER = "KO"
DEFAULT_COMPANY = "The Coca-Cola Company"

# MCP server timeout (seconds)
MCP_TIMEOUT = 90.0


class MCPTestResult:
    """Result from testing a single MCP."""
    def __init__(self, name: str):
        self.name = name
        self.status = "FAIL"
        self.data: Optional[Dict] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.item_count = 0
        self.duration_ms = 0


async def test_fundamentals(ticker: str) -> MCPTestResult:
    """Test fundamentals-basket MCP via subprocess+MCP protocol."""
    result = MCPTestResult("fundamentals")
    start = datetime.now()

    try:
        data = await call_mcp_server(
            "fundamentals-basket",
            "get_all_sources_fundamentals",
            {"ticker": ticker},
            timeout=MCP_TIMEOUT
        )
        result.data = data

        if not isinstance(data, dict):
            result.errors.append("Response is not a dict")
            return result

        if "error" in data:
            result.errors.append(f"MCP error: {data['error']}")
            return result

        # Schema validation - fundamentals uses sources.sec_edgar/sources.yahoo_finance
        sources = data.get("sources", {})
        sec_data = sources.get("sec_edgar", {})
        yahoo_data = sources.get("yahoo_finance", {})

        if not sec_data and not yahoo_data:
            result.errors.append("No SEC or Yahoo data")
        else:
            # Count only dict metrics with values (matches extraction logic)
            sec_metrics = sec_data.get("data", {}) if isinstance(sec_data, dict) else {}
            yahoo_metrics = yahoo_data.get("data", {}) if isinstance(yahoo_data, dict) else {}
            sec_count = sum(1 for v in sec_metrics.values() if isinstance(v, dict))
            yahoo_count = sum(1 for v in yahoo_metrics.values() if isinstance(v, dict))
            result.item_count = sec_count + yahoo_count
            if result.item_count == 0:
                result.warnings.append("No data items returned")

        result.status = "PASS" if not result.errors else "FAIL"

    except Exception as e:
        result.errors.append(str(e))

    result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    return result


async def test_valuation(ticker: str) -> MCPTestResult:
    """Test valuation-basket MCP via subprocess+MCP protocol."""
    result = MCPTestResult("valuation")
    start = datetime.now()

    try:
        data = await call_mcp_server(
            "valuation-basket",
            "get_all_sources_valuation",
            {"ticker": ticker},
            timeout=MCP_TIMEOUT
        )
        result.data = data

        if not isinstance(data, dict):
            result.errors.append("Response is not a dict")
            return result

        if "error" in data:
            result.errors.append(f"MCP error: {data['error']}")
            return result

        # Schema validation
        if "sources" not in data:
            result.errors.append("Missing 'sources' key")
        else:
            sources = data.get("sources", {})
            result.item_count = sum(
                len(v.get("data", {})) if isinstance(v, dict) else 0
                for v in sources.values()
            )
            if result.item_count == 0:
                result.warnings.append("No data items returned")

        result.status = "PASS" if not result.errors else "FAIL"

    except Exception as e:
        result.errors.append(str(e))

    result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    return result


async def test_volatility(ticker: str) -> MCPTestResult:
    """Test volatility-basket MCP via subprocess+MCP protocol."""
    result = MCPTestResult("volatility")
    start = datetime.now()

    try:
        data = await call_mcp_server(
            "volatility-basket",
            "get_all_sources_volatility",
            {"ticker": ticker},
            timeout=MCP_TIMEOUT
        )
        result.data = data

        if not isinstance(data, dict):
            result.errors.append("Response is not a dict")
            return result

        if "error" in data:
            result.errors.append(f"MCP error: {data['error']}")
            return result

        # Schema validation
        if "metrics" not in data:
            result.errors.append("Missing 'metrics' key")
        else:
            result.item_count = len(data.get("metrics", {}))
            if result.item_count == 0:
                result.warnings.append("No metrics returned")

        result.status = "PASS" if not result.errors else "FAIL"

    except Exception as e:
        result.errors.append(str(e))

    result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    return result


async def test_macro() -> MCPTestResult:
    """Test macro-basket MCP via subprocess+MCP protocol."""
    result = MCPTestResult("macro")
    start = datetime.now()

    try:
        data = await call_mcp_server(
            "macro-basket",
            "get_all_sources_macro",
            {},
            timeout=MCP_TIMEOUT
        )
        result.data = data

        if not isinstance(data, dict):
            result.errors.append("Response is not a dict")
            return result

        if "error" in data:
            result.errors.append(f"MCP error: {data['error']}")
            return result

        # Schema validation
        if "metrics" not in data:
            result.errors.append("Missing 'metrics' key")
        else:
            result.item_count = len(data.get("metrics", {}))
            if result.item_count == 0:
                result.warnings.append("No metrics returned")

        result.status = "PASS" if not result.errors else "FAIL"

    except Exception as e:
        result.errors.append(str(e))

    result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    return result


async def test_news(ticker: str, company_name: str) -> MCPTestResult:
    """Test news-basket MCP via subprocess+MCP protocol."""
    result = MCPTestResult("news")
    start = datetime.now()

    try:
        data = await call_mcp_server(
            "news-basket",
            "get_all_sources_news",
            {"ticker": ticker, "company_name": company_name},
            timeout=MCP_TIMEOUT
        )
        result.data = data

        if not isinstance(data, dict):
            result.errors.append("Response is not a dict")
            return result

        if "error" in data:
            result.errors.append(f"MCP error: {data['error']}")
            return result

        # Schema validation
        if "items" not in data:
            result.errors.append("Missing 'items' key")
        else:
            items = data.get("items", [])
            result.item_count = len(items)
            if result.item_count == 0:
                result.warnings.append("No news items returned")
            else:
                # Validate item schema
                for item in items[:3]:
                    if "title" not in item:
                        result.warnings.append("Item missing 'title'")
                        break
                    if "url" not in item:
                        result.warnings.append("Item missing 'url'")
                        break

        result.status = "PASS" if not result.errors else "FAIL"

    except Exception as e:
        result.errors.append(str(e))

    result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    return result


async def test_sentiment(ticker: str, company_name: str) -> MCPTestResult:
    """Test sentiment-basket MCP via subprocess+MCP protocol."""
    result = MCPTestResult("sentiment")
    start = datetime.now()

    try:
        data = await call_mcp_server(
            "sentiment-basket",
            "get_sentiment_basket",
            {"ticker": ticker, "company_name": company_name},
            timeout=MCP_TIMEOUT
        )
        result.data = data

        if not isinstance(data, dict):
            result.errors.append("Response is not a dict")
            return result

        if "error" in data:
            result.errors.append(f"MCP error: {data['error']}")
            return result

        # Schema validation
        if "items" not in data:
            result.errors.append("Missing 'items' key")
        else:
            items = data.get("items", [])
            result.item_count = len(items)
            if result.item_count == 0:
                result.warnings.append("No sentiment items returned")
            else:
                # Validate item schema
                for item in items[:3]:
                    if "title" not in item:
                        result.warnings.append("Item missing 'title'")
                        break
                    if "url" not in item:
                        result.warnings.append("Item missing 'url'")
                        break

        result.status = "PASS" if not result.errors else "FAIL"

    except Exception as e:
        result.errors.append(str(e))

    result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
    return result


async def run_all_tests(ticker: str, company_name: str) -> List[MCPTestResult]:
    """Run all MCP tests."""
    print(f"\nRunning E2E tests for {company_name} ({ticker})...")
    print("-" * 50)

    # Run tests - some in parallel, some sequential to avoid import conflicts
    results = []

    # Quantitative tests
    print("Testing fundamentals-basket...", end=" ", flush=True)
    r = await test_fundamentals(ticker)
    print(f"{r.status} ({r.duration_ms}ms)")
    results.append(r)

    print("Testing valuation-basket...", end=" ", flush=True)
    r = await test_valuation(ticker)
    print(f"{r.status} ({r.duration_ms}ms)")
    results.append(r)

    print("Testing volatility-basket...", end=" ", flush=True)
    r = await test_volatility(ticker)
    print(f"{r.status} ({r.duration_ms}ms)")
    results.append(r)

    print("Testing macro-basket...", end=" ", flush=True)
    r = await test_macro()
    print(f"{r.status} ({r.duration_ms}ms)")
    results.append(r)

    # Qualitative tests
    print("Testing news-basket...", end=" ", flush=True)
    r = await test_news(ticker, company_name)
    print(f"{r.status} ({r.duration_ms}ms)")
    results.append(r)

    print("Testing sentiment-basket...", end=" ", flush=True)
    r = await test_sentiment(ticker, company_name)
    print(f"{r.status} ({r.duration_ms}ms)")
    results.append(r)

    return results


def format_value(val: Any) -> str:
    """Format a value for display - raw output for now."""
    if val is None:
        return "-"
    # Just return string representation of value
    return str(val)


def extract_quantitative_rows(results: List[MCPTestResult], ticker: str) -> List[Dict]:
    """Extract quantitative data rows from results."""
    rows = []

    # Fundamentals - uses sources.sec_edgar/sources.yahoo_finance with nested 'data' key
    fund_result = next((r for r in results if r.name == "fundamentals"), None)
    if fund_result and fund_result.data:
        sources = fund_result.data.get("sources", {})

        # SEC EDGAR data - metrics are inside sources.sec_edgar.data
        sec_wrapper = sources.get("sec_edgar", {})
        sec_data = sec_wrapper.get("data", {}) if isinstance(sec_wrapper, dict) else {}
        for metric_name, metric_val in sec_data.items():
            if isinstance(metric_val, dict):
                rows.append({
                    "metric": metric_name,
                    "value": format_value(metric_val.get("value")),
                    "data_type": metric_val.get("data_type", "FY"),
                    "as_of": metric_val.get("end_date", "-"),
                    "filed": metric_val.get("filed", "-"),
                    "source": "SEC EDGAR",
                    "category": "Fundamentals",
                })

        # Yahoo Finance data - metrics are inside sources.yahoo_finance.data
        yahoo_wrapper = sources.get("yahoo_finance", {})
        yahoo_as_of = yahoo_wrapper.get("as_of", "-") if isinstance(yahoo_wrapper, dict) else "-"
        yahoo_data = yahoo_wrapper.get("data", {}) if isinstance(yahoo_wrapper, dict) else {}
        for metric_name, metric_val in yahoo_data.items():
            if isinstance(metric_val, dict):
                rows.append({
                    "metric": metric_name,
                    "value": format_value(metric_val.get("value")),
                    "data_type": metric_val.get("period", metric_val.get("data_type", "TTM")),
                    "as_of": metric_val.get("end_date", metric_val.get("as_of", yahoo_as_of)),
                    "filed": metric_val.get("filed", "-"),
                    "source": "Yahoo Finance",
                    "category": "Fundamentals",
                })

    # Valuation
    val_result = next((r for r in results if r.name == "valuation"), None)
    if val_result and val_result.data:
        sources = val_result.data.get("sources", {})
        as_of = val_result.data.get("as_of", "-")
        for source_name, source_data in sources.items():
            if isinstance(source_data, dict) and "data" in source_data:
                for metric_name, metric_val in source_data["data"].items():
                    # Handle both dict and scalar values
                    if isinstance(metric_val, dict):
                        value = format_value(metric_val.get("value"))
                        data_type = metric_val.get("data_type", "-")
                        metric_as_of = metric_val.get("as_of", as_of)
                    else:
                        value = format_value(metric_val)
                        data_type = "-"
                        metric_as_of = as_of
                    rows.append({
                        "metric": metric_name,
                        "value": value,
                        "data_type": data_type,
                        "as_of": metric_as_of,
                        "source": source_name,
                        "category": "Valuation",
                    })

    # Volatility
    vol_result = next((r for r in results if r.name == "volatility"), None)
    if vol_result and vol_result.data:
        metrics = vol_result.data.get("metrics", {})
        for metric_name, metric_val in metrics.items():
            if isinstance(metric_val, dict):
                rows.append({
                    "metric": metric_name,
                    "value": format_value(metric_val.get("value")),
                    "data_type": metric_val.get("data_type", "-"),
                    "as_of": metric_val.get("as_of", "-"),
                    "filed": "-",
                    "source": metric_val.get("source", "-"),
                    "category": "Volatility",
                })

    # Macro
    macro_result = next((r for r in results if r.name == "macro"), None)
    if macro_result and macro_result.data:
        metrics = macro_result.data.get("metrics", {})
        for metric_name, metric_val in metrics.items():
            if isinstance(metric_val, dict):
                rows.append({
                    "metric": metric_name,
                    "value": format_value(metric_val.get("value")),
                    "data_type": metric_val.get("data_type", "-"),
                    "as_of": metric_val.get("as_of", "-"),
                    "filed": "-",
                    "source": metric_val.get("source", "-"),
                    "category": "Macro",
                })

    return rows


def extract_date(item: Dict) -> str:
    """Extract date (YYYY-MM-DD) from item, checking both date and datetime fields."""
    # Try 'date' first, then 'datetime'
    val = item.get("date") or item.get("datetime") or "-"
    if val == "-":
        return val
    # Extract just the date portion (first 10 chars: YYYY-MM-DD)
    val_str = str(val)
    if len(val_str) >= 10:
        return val_str[:10]
    return val_str


def extract_qualitative_rows(results: List[MCPTestResult]) -> List[Dict]:
    """Extract qualitative data rows from results."""
    rows = []

    # News
    news_result = next((r for r in results if r.name == "news"), None)
    if news_result and news_result.data:
        items = news_result.data.get("items", [])
        for item in items[:10]:  # Limit to 10
            rows.append({
                "title": item.get("title", "-")[:80],
                "date": extract_date(item),
                "source": item.get("source", "-"),
                "subreddit": "-",
                "url": item.get("url", "-"),
                "category": "News",
            })

    # Sentiment
    sent_result = next((r for r in results if r.name == "sentiment"), None)
    if sent_result and sent_result.data:
        items = sent_result.data.get("items", [])
        for item in items[:10]:  # Limit to 10
            subreddit = item.get("subreddit") or "-"
            rows.append({
                "title": item.get("title", "-")[:80],
                "date": extract_date(item),
                "source": item.get("source", "-"),
                "subreddit": subreddit if subreddit != "None" else "-",
                "url": item.get("url", "-"),
                "category": "Sentiment",
            })

    return rows


def generate_report(results: List[MCPTestResult], ticker: str, company_name: str) -> str:
    """Generate markdown report."""
    # Expected item counts per MCP (quantitative only - dict metrics with values)
    expected_counts = {
        "fundamentals": 9,  # SEC EDGAR (5 universal) + Yahoo Finance (4 supplementary)
        "valuation": 11,     # Yahoo Finance only (11 universal, excludes ev_ebitda)
        "volatility": 5,     # VIX, VXN, beta, historical_vol, implied_vol
        "macro": 4,          # GDP, interest_rate, CPI, unemployment
    }

    lines = [
        f"# MCP E2E Test Report: {company_name} ({ticker})",
        "",
        "## Summary",
        "",
        "| S/N | MCP | Status | Expected | Actual | Duration | Errors | Warnings |",
        "|-----|-----|--------|----------|--------|----------|--------|----------|",
    ]

    for i, r in enumerate(results, 1):
        expected = expected_counts.get(r.name, "-")
        errors = "; ".join(r.errors) if r.errors else "-"
        warnings = "; ".join(r.warnings) if r.warnings else "-"
        lines.append(f"| {i} | {r.name} | {r.status} | {expected} | {r.item_count} | {r.duration_ms}ms | {errors} | {warnings} |")

    # Quantitative Data
    lines.extend([
        "",
        "---",
        "",
        "## Quantitative Data",
        "",
        "| S/N | Metric | Value | Data Type | As Of | Source | Category |",
        "|-----|--------|-------|-----------|-------|--------|----------|",
    ])

    quant_rows = extract_quantitative_rows(results, ticker)
    for i, row in enumerate(quant_rows, 1):
        lines.append(f"| {i} | {row['metric']} | {row['value']} | {row['data_type']} | {row['as_of']} | {row['source']} | {row['category']} |")

    if not quant_rows:
        lines.append("| - | - | - | - | - | - | - |")

    # Qualitative Data
    lines.extend([
        "",
        "---",
        "",
        "## Qualitative Data",
        "",
        "| S/N | Title | Date | Source | Subreddit | URL | Category |",
        "|-----|-------|------|--------|-----------|-----|----------|",
    ])

    qual_rows = extract_qualitative_rows(results)
    for i, row in enumerate(qual_rows, 1):
        url_link = f"[Link]({row['url']})" if row['url'] != "-" else "-"
        lines.append(f"| {i} | {row['title']} | {row['date']} | {row['source']} | {row['subreddit']} | {url_link} | {row['category']} |")

    if not qual_rows:
        lines.append("| - | - | - | - | - | - | - |")

    lines.append("")
    return "\n".join(lines)


def main():
    """Main entry point."""
    # Parse args
    ticker = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TICKER
    company_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_COMPANY

    # Run tests
    results = asyncio.run(run_all_tests(ticker, company_name))

    # Generate report
    report = generate_report(results, ticker, company_name)

    # Write report
    output_path = PROJECT_ROOT / "docs" / f"mcp_test_report_{ticker}.md"
    output_path.write_text(report)

    print("-" * 50)
    print(f"Report generated: {output_path}")

    # Summary
    passed = sum(1 for r in results if r.status == "PASS")
    total = len(results)
    print(f"\nResult: {passed}/{total} MCPs passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
