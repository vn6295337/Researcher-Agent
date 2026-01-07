"""
MCP Client - TRUE MCP protocol via subprocess stdio.

Implements proper MCP handshake:
1. Send 'initialize' request
2. Receive initialization response
3. Send 'initialized' notification
4. Send 'tools/call' request
5. Parse response
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

# Base path for MCP servers
MCP_SERVERS_PATH = Path(__file__).parent / "mcp-servers"

# Configurable delay for granular progress events (ms)
METRIC_DELAY_MS = int(os.getenv("METRIC_DELAY_MS", "300"))


async def emit_metric(
    progress_callback: Optional[Callable],
    source: str,
    metric: str,
    value: Any,
    end_date: str = None,
    fiscal_year: int = None,
    form: str = None
):
    """Emit a metric event as a structured payload with optional temporal data."""
    if progress_callback:
        payload = {
            "source": source,
            "metric": metric,
            "value": value,
            "end_date": end_date,
            "fiscal_year": fiscal_year,
            "form": form,
        }
        logger.debug(f"emit_metric payload: {json.dumps(payload, default=str)}")
        progress_callback(payload)
        await asyncio.sleep(METRIC_DELAY_MS / 1000)


async def call_mcp_server(
    server_name: str,
    tool_name: str,
    arguments: dict,
    timeout: float = 30.0
) -> dict:
    """
    Call an MCP server tool via subprocess stdio using TRUE MCP protocol.

    Args:
        server_name: Name of the MCP server directory (e.g., 'financials-basket')
        tool_name: Name of the tool to call (e.g., 'get_sec_fundamentals')
        arguments: Dict of arguments to pass to the tool
        timeout: Timeout in seconds

    Returns:
        Dict with tool result or error
    """
    server_path = MCP_SERVERS_PATH / server_name / "server.py"

    if not server_path.exists():
        return {"error": f"MCP server not found: {server_name}"}

    # MCP Protocol: Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "research-service",
                "version": "1.0.0"
            }
        }
    }

    # MCP Protocol: Initialized notification (no id = notification)
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }

    # MCP Protocol: Tool call request
    tool_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    try:
        # Start the MCP server process
        process = await asyncio.create_subprocess_exec(
            "python3", str(server_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(server_path.parent),
            env={**os.environ}
        )

        # Build the full request sequence (newline-delimited JSON)
        requests = (
            json.dumps(init_request) + "\n" +
            json.dumps(initialized_notification) + "\n" +
            json.dumps(tool_request) + "\n"
        )

        # Write requests to stdin WITHOUT closing it yet
        process.stdin.write(requests.encode())
        await process.stdin.drain()

        # Read stdout line by line until we get the tool response (id=2)
        response_text = ""
        tool_response = None

        try:
            async def read_responses():
                nonlocal response_text, tool_response
                while True:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=timeout
                    )
                    if not line:
                        break
                    line_str = line.decode().strip()
                    response_text += line_str + "\n"

                    if line_str.startswith("{"):
                        try:
                            response = json.loads(line_str)
                            # Look for the tool call response (id=2)
                            if response.get("id") == 2:
                                tool_response = response
                                return  # Got what we need
                        except json.JSONDecodeError:
                            continue

            await read_responses()

        except asyncio.TimeoutError:
            pass  # Continue to process what we have

        # Now close stdin to signal EOF to the server
        process.stdin.close()
        await process.stdin.wait_closed()

        # Give the process a moment to exit gracefully
        try:
            await asyncio.wait_for(process.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

        # Read any remaining stderr
        stderr_data = await process.stderr.read()
        stderr_text = stderr_data.decode().strip() if stderr_data else ""
        if stderr_text:
            logger.debug(f"MCP server {server_name} stderr: {stderr_text[:500]}")

        # Process the tool response we captured
        if tool_response:
            if "result" in tool_response:
                # Extract text content from MCP response
                result = tool_response["result"]
                if isinstance(result, dict) and "content" in result:
                    # MCP SDK format: {"content": [{"type": "text", "text": "..."}]}
                    content_list = result.get("content", [])
                    if content_list and isinstance(content_list, list):
                        for content in content_list:
                            if isinstance(content, dict) and content.get("type") == "text":
                                try:
                                    return json.loads(content.get("text", "{}"))
                                except json.JSONDecodeError:
                                    return {"raw_text": content.get("text", "")}
                return result
            elif "error" in tool_response:
                return {"error": tool_response["error"]}

        # Fallback: no tool response captured
        return {"error": f"No tool response received. stdout: {response_text[:200]}"}

    except Exception as e:
        logger.error(f"Error calling MCP server {server_name}: {e}")
        return {"error": str(e)}


async def call_financials_mcp(ticker: str) -> dict:
    """Fetch SEC fundamentals for a ticker."""
    return await call_mcp_server(
        "financials-basket",
        "get_sec_fundamentals",
        {"ticker": ticker}
    )


async def call_volatility_mcp(ticker: str) -> dict:
    """Fetch volatility metrics for a ticker."""
    return await call_mcp_server(
        "volatility-basket",
        "get_volatility_basket",
        {"ticker": ticker}
    )


async def call_macro_mcp() -> dict:
    """Fetch macroeconomic indicators."""
    return await call_mcp_server(
        "macro-basket",
        "get_macro_basket",
        {}
    )


async def call_valuation_mcp(ticker: str) -> dict:
    """Fetch valuation ratios for a ticker."""
    return await call_mcp_server(
        "valuation-basket",
        "get_valuation_basket",
        {"ticker": ticker}
    )


async def call_news_mcp(ticker: str, company_name: str = "") -> dict:
    """Fetch news for a company."""
    args = {"ticker": ticker}
    if company_name:
        args["company_name"] = company_name
    return await call_mcp_server(
        "news-basket",
        "search_company_news",
        args
    )


async def call_sentiment_mcp(ticker: str, company_name: str = "") -> dict:
    """Fetch sentiment metrics for a ticker."""
    return await call_mcp_server(
        "sentiment-basket",
        "get_sentiment_basket",
        {"ticker": ticker, "company_name": company_name}
    )


async def _extract_and_emit_metrics(
    source: str,
    result: dict,
    progress_callback: Optional[Callable]
) -> None:
    """Extract metrics from MCP result and emit via callback."""
    if not progress_callback or not result or "error" in result:
        return

    if source == "financials":
        financials = result.get("financials") or {}
        debt = result.get("debt") or {}
        # Extract temporal data with metrics
        revenue = financials.get("revenue") or {}
        if isinstance(revenue, dict) and revenue.get("value"):
            await emit_metric(
                progress_callback, source, "revenue", revenue["value"],
                end_date=revenue.get("end_date"),
                fiscal_year=revenue.get("fiscal_year"),
                form=revenue.get("form")
            )
        net_margin = financials.get("net_margin") or financials.get("net_margin_pct")
        if net_margin is not None:
            await emit_metric(progress_callback, source, "net_margin", net_margin)
        eps = financials.get("eps") or {}
        if isinstance(eps, dict) and eps.get("value"):
            await emit_metric(
                progress_callback, source, "EPS", eps["value"],
                end_date=eps.get("end_date"),
                fiscal_year=eps.get("fiscal_year"),
                form=eps.get("form")
            )
        debt_to_equity = debt.get("debt_to_equity")
        if debt_to_equity is not None:
            await emit_metric(progress_callback, source, "debt_to_equity", debt_to_equity)

    elif source == "volatility":
        metrics = result.get("metrics") or {}
        beta = metrics.get("beta") or {}
        if isinstance(beta, dict) and beta.get("value") is not None:
            await emit_metric(progress_callback, source, "beta", beta["value"])
        vix = metrics.get("vix") or {}
        if isinstance(vix, dict) and vix.get("value") is not None:
            await emit_metric(progress_callback, source, "VIX", vix["value"])
        hist_vol = metrics.get("historical_volatility") or {}
        if isinstance(hist_vol, dict) and hist_vol.get("value") is not None:
            await emit_metric(progress_callback, source, "hist_vol", hist_vol["value"])

    elif source == "macro":
        metrics = result.get("metrics") or {}
        gdp = metrics.get("gdp_growth") or {}
        if isinstance(gdp, dict) and gdp.get("value") is not None:
            await emit_metric(progress_callback, source, "GDP_growth", gdp["value"])
        interest = metrics.get("interest_rate") or {}
        if isinstance(interest, dict) and interest.get("value") is not None:
            await emit_metric(progress_callback, source, "interest_rate", interest["value"])
        inflation = metrics.get("cpi_inflation") or {}
        if isinstance(inflation, dict) and inflation.get("value") is not None:
            await emit_metric(progress_callback, source, "inflation", inflation["value"])
        unemployment = metrics.get("unemployment") or {}
        if isinstance(unemployment, dict) and unemployment.get("value") is not None:
            await emit_metric(progress_callback, source, "unemployment", unemployment["value"])

    elif source == "valuation":
        metrics = result.get("metrics") or {}
        pe = metrics.get("pe_ratio") or {}
        pe_val = None
        if isinstance(pe, dict):
            pe_val = pe.get("trailing") or pe.get("forward")
        elif isinstance(pe, (int, float)):
            pe_val = pe
        if pe_val is not None:
            await emit_metric(progress_callback, source, "P/E", pe_val)
        pb_ratio = metrics.get("pb_ratio")
        if pb_ratio is not None:
            await emit_metric(progress_callback, source, "P/B", pb_ratio)
        ps_ratio = metrics.get("ps_ratio")
        if ps_ratio is not None:
            await emit_metric(progress_callback, source, "P/S", ps_ratio)
        ev_ebitda = metrics.get("ev_ebitda")
        if ev_ebitda is not None:
            await emit_metric(progress_callback, source, "EV/EBITDA", ev_ebitda)

    elif source == "news":
        articles = result.get("articles") or []
        if articles and isinstance(articles, list) and len(articles) > 0:
            await emit_metric(progress_callback, source, "articles_found", len(articles))
        else:
            await emit_metric(progress_callback, source, "status", "No recent news found")

    elif source == "sentiment":
        has_data = False
        composite = result.get("composite_score")
        if composite is not None:
            await emit_metric(progress_callback, source, "composite_score", composite)
            has_data = True
        metrics = result.get("metrics") or {}
        finnhub = metrics.get("finnhub") or {}
        if isinstance(finnhub, dict) and finnhub.get("sentiment_score") is not None:
            await emit_metric(progress_callback, source, "finnhub_score", finnhub["sentiment_score"])
            has_data = True
        if not has_data:
            await emit_metric(progress_callback, source, "status", "No sentiment data available")


def _aggregate_swot(metrics: dict, sources_available: list) -> dict:
    """Aggregate SWOT summaries from all MCP sources."""
    aggregated_swot = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": []
    }

    for source in sources_available:
        source_data = metrics.get(source, {})
        swot = source_data.get("swot_summary", {})
        for category in aggregated_swot:
            items = swot.get(category, [])
            if items:
                aggregated_swot[category].extend(items)

    return aggregated_swot


async def fetch_all_research_data(
    ticker: str,
    company_name: str,
    progress_callback: Optional[Callable] = None
) -> dict:
    """
    Fetch data from all 6 MCP servers in parallel using TRUE MCP protocol.

    Args:
        ticker: Stock ticker symbol
        company_name: Company name
        progress_callback: Optional callback for granular metric events (source, metric, value)

    Returns aggregated results with sources_available, sources_failed, and aggregated_swot.
    """
    logger.info(f"Fetching from MCP servers for {ticker} ({company_name})...")

    # MCP call functions mapped by name
    mcp_functions = {
        "financials": lambda: call_financials_mcp(ticker),
        "volatility": lambda: call_volatility_mcp(ticker),
        "macro": lambda: call_macro_mcp(),
        "valuation": lambda: call_valuation_mcp(ticker),
        "news": lambda: call_news_mcp(ticker, company_name),
        "sentiment": lambda: call_sentiment_mcp(ticker, company_name),
    }
    mcp_names = list(mcp_functions.keys())

    # Call all MCPs in parallel
    results = await asyncio.gather(
        *[mcp_functions[name]() for name in mcp_names],
        return_exceptions=True
    )

    metrics = {}
    sources_available = []
    sources_failed = []
    failed_for_retry = []

    # First pass - identify successes and failures, emit metrics
    for name, result in zip(mcp_names, results):
        if isinstance(result, Exception):
            failed_for_retry.append(name)
            metrics[name] = {"error": str(result)}
            logger.warning(f"MCP {name} failed: {result}")
        elif isinstance(result, dict) and "error" in result:
            failed_for_retry.append(name)
            metrics[name] = result
            logger.warning(f"MCP {name} error: {result.get('error', 'Unknown')[:50]}")
        else:
            sources_available.append(name)
            metrics[name] = result
            # Emit metrics for this source
            await _extract_and_emit_metrics(name, result, progress_callback)
            logger.info(f"MCP {name} fetched successfully")

    # Automatic retry once for failed MCPs
    if failed_for_retry:
        logger.info(f"Retrying {len(failed_for_retry)} failed MCP servers: {failed_for_retry}")

        retry_results = await asyncio.gather(
            *[mcp_functions[name]() for name in failed_for_retry],
            return_exceptions=True
        )

        for name, result in zip(failed_for_retry, retry_results):
            if isinstance(result, Exception):
                sources_failed.append(name)
                metrics[name] = {"error": str(result), "retried": True}
                logger.warning(f"MCP {name} failed after retry: {result}")
            elif isinstance(result, dict) and "error" in result:
                sources_failed.append(name)
                metrics[name] = {**result, "retried": True}
                logger.warning(f"MCP {name} failed after retry: {result.get('error')}")
            else:
                sources_available.append(name)
                metrics[name] = result
                # Emit metrics for this source
                await _extract_and_emit_metrics(name, result, progress_callback)
                logger.info(f"MCP {name} succeeded on retry")

    # Build aggregated SWOT
    aggregated_swot = _aggregate_swot(metrics, sources_available)

    data = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "sources_available": sources_available,
        "sources_failed": sources_failed,
        "metrics": metrics,
        "aggregated_swot": aggregated_swot,
        "generated_at": datetime.now().isoformat()
    }

    logger.info(f"Research complete: {len(sources_available)} sources, {len(sources_failed)} failed")

    return data
