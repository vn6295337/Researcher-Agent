"""
MCP Client - TRUE MCP protocol via subprocess stdio.

Implements proper MCP handshake:
1. Send 'initialize' request
2. Receive initialization response
3. Send 'initialized' notification
4. Send 'tools/call' request
5. Parse response

Also supports HTTP-based load-balanced calls for fundamentals-basket.
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Any

import httpx

logger = logging.getLogger(__name__)

# Base path for MCP servers
MCP_SERVERS_PATH = Path(__file__).parent / "mcp-servers"

# Configurable delay for granular progress events (ms)
# Set to 0 for completeness-first mode (no artificial UI delays)
METRIC_DELAY_MS = int(os.getenv("METRIC_DELAY_MS", "0"))

# =============================================================================
# HTTP LOAD BALANCER CONFIGURATION
# =============================================================================

# Financials HTTP load balancer URL (nginx on port 8080)
FINANCIALS_HTTP_URL = os.getenv("FINANCIALS_HTTP_URL", "http://localhost:8080")

# Toggle HTTP mode (set to "false" to use subprocess MCP)
USE_HTTP_FINANCIALS = os.getenv("USE_HTTP_FINANCIALS", "false").lower() == "true"

# HTTP client timeout (increased for completeness-first mode)
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "90.0"))


# =============================================================================
# HTTP CLIENT FOR LOAD-BALANCED CALLS
# =============================================================================

async def call_fundamentals_http(tool_name: str, arguments: dict, timeout: float = None) -> dict:
    """
    Call fundamentals-basket via HTTP load balancer (nginx).

    This bypasses MCP subprocess spawning for better performance.
    Requires the HTTP cluster to be running (./start_cluster.sh).

    Args:
        tool_name: Name of the tool (e.g., 'get_sec_fundamentals')
        arguments: Tool arguments dict
        timeout: Request timeout in seconds

    Returns:
        Tool result dict or error dict
    """
    timeout = timeout or HTTP_TIMEOUT
    url = f"{FINANCIALS_HTTP_URL}/tools/{tool_name}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=arguments)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        logger.error(f"HTTP timeout calling {tool_name}: {timeout}s")
        return {"error": f"HTTP timeout after {timeout}s", "tool": tool_name}

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling {tool_name}: {e.response.status_code}")
        return {"error": f"HTTP {e.response.status_code}", "tool": tool_name}

    except httpx.ConnectError:
        logger.warning(f"HTTP connection failed for {tool_name}, falling back to subprocess")
        # Fall back to subprocess MCP if HTTP cluster is not running
        return await call_mcp_server("fundamentals-basket", tool_name, arguments, timeout)

    except Exception as e:
        logger.error(f"HTTP error calling {tool_name}: {e}")
        return {"error": str(e), "tool": tool_name}


async def check_fundamentals_http_health() -> bool:
    """
    Check if the fundamentals HTTP cluster is healthy.

    Returns:
        True if cluster is responding, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FINANCIALS_HTTP_URL}/health")
            return response.status_code == 200
    except Exception:
        return False


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
    timeout: float = 90.0
) -> dict:
    """
    Call an MCP server tool via subprocess stdio using proper MCP protocol sequencing.

    Protocol sequence:
    1. Send initialize request -> wait for response (id=1)
    2. Send initialized notification
    3. Send tools/call request -> wait for response (id=2)
    4. Clean up

    Args:
        server_name: Name of the MCP server directory (e.g., 'fundamentals-basket')
        tool_name: Name of the tool to call (e.g., 'get_sec_fundamentals')
        arguments: Dict of arguments to pass to the tool
        timeout: Total timeout in seconds (default 60s for external API calls)

    Returns:
        Dict with tool result or error
    """
    server_path = MCP_SERVERS_PATH / server_name / "server.py"

    if not server_path.exists():
        return {"error": f"MCP server not found: {server_name}"}

    process = None
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

        async def send_message(msg: dict):
            """Send a JSON-RPC message to the server."""
            data = json.dumps(msg) + "\n"
            process.stdin.write(data.encode())
            await process.stdin.drain()

        async def read_response(expected_id: int, phase_timeout: float) -> dict:
            """Read and parse JSON-RPC response with expected id."""
            buffer = ""
            start_time = asyncio.get_event_loop().time()

            while True:
                remaining = phase_timeout - (asyncio.get_event_loop().time() - start_time)
                if remaining <= 0:
                    raise asyncio.TimeoutError(f"Timeout waiting for response id={expected_id}")

                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=min(remaining, 5.0)  # Check every 5s
                    )
                except asyncio.TimeoutError:
                    continue  # Keep trying until phase_timeout

                if not line:
                    # EOF - server closed stdout
                    raise EOFError(f"Server closed stdout before sending response id={expected_id}")

                line_str = line.decode().strip()
                if not line_str:
                    continue

                # Try to parse as JSON
                # Handle case where line might contain non-JSON prefix (logs)
                json_start = line_str.find('{')
                if json_start == -1:
                    continue

                try:
                    response = json.loads(line_str[json_start:])
                    if isinstance(response, dict):
                        # Check if this is the response we're waiting for
                        if response.get("id") == expected_id:
                            return response
                        # Also check for error responses
                        if "error" in response and response.get("id") == expected_id:
                            return response
                except json.JSONDecodeError:
                    # Might be partial JSON, accumulate in buffer
                    buffer += line_str
                    try:
                        response = json.loads(buffer)
                        if response.get("id") == expected_id:
                            return response
                        buffer = ""  # Reset if we got valid JSON but wrong id
                    except json.JSONDecodeError:
                        pass  # Keep accumulating

        # Phase 1: Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "research-service", "version": "1.0.0"}
            }
        }
        await send_message(init_request)
        init_response = await read_response(expected_id=1, phase_timeout=20.0)

        if "error" in init_response:
            return {"error": f"Initialize failed: {init_response['error']}"}

        # Phase 2: Send initialized notification (no response expected)
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await send_message(initialized_notification)
        await asyncio.sleep(0.05)  # Brief pause for server to process

        # Phase 3: Tool call
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        await send_message(tool_request)
        tool_response = await read_response(expected_id=2, phase_timeout=timeout)

        # Process tool response
        if "error" in tool_response:
            return {"error": f"Tool call failed: {tool_response['error']}"}

        if "result" in tool_response:
            result = tool_response["result"]
            # MCP SDK format: {"content": [{"type": "text", "text": "..."}]}
            if isinstance(result, dict) and "content" in result:
                content_list = result.get("content", [])
                if content_list and isinstance(content_list, list):
                    for content in content_list:
                        if isinstance(content, dict) and content.get("type") == "text":
                            try:
                                return json.loads(content.get("text", "{}"))
                            except json.JSONDecodeError:
                                return {"raw_text": content.get("text", "")}
            return result

        return {"error": "No result in tool response"}

    except asyncio.TimeoutError as e:
        logger.warning(f"MCP {server_name} timeout: {e}")
        return {"error": f"Timeout: {e}"}
    except EOFError as e:
        logger.warning(f"MCP {server_name} EOF: {e}")
        return {"error": f"Server closed: {e}"}
    except Exception as e:
        logger.error(f"MCP {server_name} error: {e}")
        return {"error": str(e)}
    finally:
        # Clean up process
        if process:
            try:
                process.stdin.close()
            except:
                pass
            try:
                # Give process 2s to exit gracefully
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            # Log stderr if any
            try:
                stderr_data = await asyncio.wait_for(process.stderr.read(), timeout=1.0)
                if stderr_data:
                    stderr_text = stderr_data.decode().strip()
                    if stderr_text:
                        logger.debug(f"MCP {server_name} stderr: {stderr_text[:500]}")
            except:
                pass


async def call_fundamentals_mcp(ticker: str) -> dict:
    """
    Fetch SEC fundamentals for a ticker.

    Uses HTTP load balancer if USE_HTTP_FINANCIALS=true, otherwise subprocess MCP.
    """
    if USE_HTTP_FINANCIALS:
        return await call_fundamentals_http("get_sec_fundamentals", {"ticker": ticker})
    return await call_mcp_server(
        "fundamentals-basket",
        "get_sec_fundamentals",
        {"ticker": ticker}
    )


async def call_fundamentals_all_sources_mcp(ticker: str) -> dict:
    """
    Fetch fundamentals from ALL sources (SEC EDGAR + Yahoo Finance).

    Uses HTTP load balancer if USE_HTTP_FINANCIALS=true, otherwise subprocess MCP.
    """
    if USE_HTTP_FINANCIALS:
        return await call_fundamentals_http("get_all_sources_fundamentals", {"ticker": ticker})
    return await call_mcp_server(
        "fundamentals-basket",
        "get_all_sources_fundamentals",
        {"ticker": ticker}
    )


async def call_volatility_mcp(ticker: str) -> dict:
    """Fetch volatility metrics for a ticker."""
    return await call_mcp_server(
        "volatility-basket",
        "get_volatility_basket",
        {"ticker": ticker}
    )


async def call_volatility_all_sources_mcp(ticker: str) -> dict:
    """Fetch volatility from ALL sources (Yahoo + Alpha Vantage + Tradier)."""
    return await call_mcp_server(
        "volatility-basket",
        "get_all_sources_volatility",
        {"ticker": ticker}
    )


async def call_macro_mcp() -> dict:
    """Fetch macroeconomic indicators."""
    return await call_mcp_server(
        "macro-basket",
        "get_macro_basket",
        {}
    )


async def call_macro_all_sources_mcp() -> dict:
    """Fetch macro from ALL sources (BEA/BLS primary + FRED fallback)."""
    return await call_mcp_server(
        "macro-basket",
        "get_all_sources_macro",
        {}
    )


async def call_valuation_mcp(ticker: str) -> dict:
    """Fetch valuation ratios for a ticker."""
    return await call_mcp_server(
        "valuation-basket",
        "get_valuation_basket",
        {"ticker": ticker}
    )


async def call_valuation_all_sources_mcp(ticker: str) -> dict:
    """Fetch valuation from ALL sources (Yahoo Finance + Alpha Vantage)."""
    return await call_mcp_server(
        "valuation-basket",
        "get_all_sources_valuation",
        {"ticker": ticker}
    )


async def call_news_mcp(ticker: str, company_name: str = "") -> dict:
    """Fetch news for a company."""
    args = {"ticker": ticker}
    if company_name:
        args["company_name"] = company_name
    return await call_mcp_server(
        "news-basket",
        "get_all_sources_news",
        args
    )


async def call_sentiment_mcp(ticker: str, company_name: str = "") -> dict:
    """Fetch sentiment metrics for a ticker."""
    return await call_mcp_server(
        "sentiment-basket",
        "get_sentiment_basket",
        {"ticker": ticker, "company_name": company_name}
    )


# =============================================================================
# SCHEMA NORMALIZERS
# Convert MCP-emitted schemas to analyzer-expected format
# =============================================================================

def _normalize_volatility(raw: dict) -> dict:
    """
    Normalize volatility schema.
    Input:  {"metrics": {"vix": {...}, "beta": {...}, ...}}
    Output: {"yahoo_finance": {"data": {...}}, "market_volatility_context": {...}}
    """
    if not raw or "error" in raw:
        return raw

    metrics = raw.get("metrics", {})

    # Extract VIX/VXN for market context
    vix = metrics.get("vix", {})
    vxn = metrics.get("vxn", {})

    # Extract stock-specific metrics for yahoo_finance
    beta = metrics.get("beta", {})
    hist_vol = metrics.get("historical_volatility", {})
    impl_vol = metrics.get("implied_volatility", {})

    return {
        "yahoo_finance": {
            "source": "Yahoo Finance",
            "data": {
                "beta": beta,
                "historical_volatility": hist_vol,
                "implied_volatility": impl_vol,
            }
        },
        "market_volatility_context": {
            "vix": {"value": vix.get("value"), "date": vix.get("as_of")},
            "vxn": {"value": vxn.get("value"), "date": vxn.get("as_of")},
        },
        "source": raw.get("source"),
        "as_of": raw.get("as_of"),
    }


def _normalize_macro(raw: dict) -> dict:
    """
    Normalize macro schema.
    Input:  {"metrics": {"gdp_growth": {...}, "interest_rate": {...}, ...}}
    Output: {"bea_bls": {"data": {...}}, "fred": {"data": {...}}}
    """
    if not raw or "error" in raw:
        return raw

    metrics = raw.get("metrics", {})

    gdp = metrics.get("gdp_growth", {})
    cpi = metrics.get("cpi_inflation", {})
    unemp = metrics.get("unemployment", {})
    interest = metrics.get("interest_rate", {})

    # BEA/BLS: GDP, CPI, unemployment (primary sources)
    # FRED: interest_rate (and fallback for others)
    return {
        "bea_bls": {
            "source": "BEA/BLS",
            "data": {
                "gdp_growth": {"value": gdp.get("value"), "date": gdp.get("as_of")},
                "cpi_inflation": {"value": cpi.get("value"), "date": cpi.get("as_of")},
                "unemployment": {"value": unemp.get("value"), "date": unemp.get("as_of")},
            }
        },
        "fred": {
            "source": "FRED",
            "data": {
                "interest_rate": {"value": interest.get("value"), "date": interest.get("as_of")},
                "gdp_growth": {"value": gdp.get("value"), "date": gdp.get("as_of")} if gdp.get("fallback") else None,
                "cpi_inflation": {"value": cpi.get("value"), "date": cpi.get("as_of")} if cpi.get("fallback") else None,
                "unemployment": {"value": unemp.get("value"), "date": unemp.get("as_of")} if unemp.get("fallback") else None,
            }
        },
        "source": raw.get("source"),
        "as_of": raw.get("as_of"),
    }


def _normalize_valuation(raw: dict) -> dict:
    """
    Normalize valuation schema.
    Input:  {"sources": {"yahoo_finance": {...}, "alpha_vantage": {...}}}
    Output: {"yahoo_finance": {"data": {...}}, "alpha_vantage": {"data": {...}}}
    """
    if not raw or "error" in raw:
        return raw

    sources = raw.get("sources", {})

    result = {
        "source": raw.get("source"),
        "as_of": raw.get("as_of"),
    }

    # Flatten sources to top level
    if "yahoo_finance" in sources:
        result["yahoo_finance"] = sources["yahoo_finance"]
    if "alpha_vantage" in sources:
        result["alpha_vantage"] = sources["alpha_vantage"]

    return result


def _normalize_fundamentals(raw: dict) -> dict:
    """
    Normalize fundamentals schema.
    Input:  {"sources": {"sec_edgar": {...}, "yahoo_finance": {...}}}
    Output: {"sec_edgar": {"data": {...}}, "yahoo_finance": {"data": {...}}}
    """
    if not raw or "error" in raw:
        return raw

    sources = raw.get("sources", {})

    result = {
        "source": raw.get("source"),
        "as_of": raw.get("as_of"),
        "ticker": raw.get("ticker"),
    }

    # Flatten sources to top level
    if "sec_edgar" in sources:
        result["sec_edgar"] = sources["sec_edgar"]
    if "yahoo_finance" in sources:
        result["yahoo_finance"] = sources["yahoo_finance"]

    return result


def _get_nested_value(data: dict, *keys):
    """Safely get nested value from dict, returns None if not found."""
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


async def _extract_and_emit_metrics(
    source: str,
    result: dict,
    progress_callback: Optional[Callable]
) -> None:
    """Extract metrics from MCP result and emit via callback.

    Handles multi-source structures from _all_sources endpoints:
    - fundamentals: {"sec_edgar": {...}, "yahoo_finance": {...}}
    - valuation: {"yahoo_finance": {...}, "alpha_vantage": {...}}
    - volatility: {"yahoo_finance": {...}, "alpha_vantage": {...}, "market_volatility_context": {...}}
    - macro: {"bea_bls": {...}, "fred": {...}}
    """
    if not progress_callback or not result or "error" in result:
        return

    if source == "fundamentals":
        # Multi-source structure: {"sec_edgar": {"data": {...}}, "yahoo_finance": {"data": {...}}}
        sec_data = _get_nested_value(result, "sec_edgar", "data") or {}
        yf_data = _get_nested_value(result, "yahoo_finance", "data") or {}

        # Revenue - prefer SEC EDGAR (primary source)
        revenue = sec_data.get("revenue") or yf_data.get("revenue") or {}
        if isinstance(revenue, dict) and revenue.get("value"):
            await emit_metric(
                progress_callback, source, "revenue", revenue["value"],
                end_date=revenue.get("end_date"),
                fiscal_year=revenue.get("fiscal_year"),
                form=revenue.get("form")
            )
        elif isinstance(revenue, (int, float)):
            await emit_metric(progress_callback, source, "revenue", revenue)

        # Net margin
        net_margin = sec_data.get("net_margin_pct") or yf_data.get("net_margin_pct") or {}
        if isinstance(net_margin, dict) and net_margin.get("value") is not None:
            await emit_metric(
                progress_callback, source, "net_margin", net_margin["value"],
                end_date=net_margin.get("end_date"),
                fiscal_year=net_margin.get("fiscal_year"),
                form=net_margin.get("form")
            )
        elif isinstance(net_margin, (int, float)):
            await emit_metric(progress_callback, source, "net_margin", net_margin)

        # EPS
        eps = sec_data.get("eps") or yf_data.get("eps") or {}
        if isinstance(eps, dict) and eps.get("value"):
            await emit_metric(
                progress_callback, source, "EPS", eps["value"],
                end_date=eps.get("end_date"),
                fiscal_year=eps.get("fiscal_year"),
                form=eps.get("form")
            )
        elif isinstance(eps, (int, float)):
            await emit_metric(progress_callback, source, "EPS", eps)

        # Debt to Equity
        debt_to_equity = sec_data.get("debt_to_equity") or yf_data.get("debt_to_equity")
        if isinstance(debt_to_equity, dict) and debt_to_equity.get("value") is not None:
            await emit_metric(
                progress_callback, source, "debt_to_equity", debt_to_equity["value"],
                end_date=debt_to_equity.get("end_date"),
                fiscal_year=debt_to_equity.get("fiscal_year"),
                form=debt_to_equity.get("form")
            )
        elif isinstance(debt_to_equity, (int, float)):
            await emit_metric(progress_callback, source, "debt_to_equity", debt_to_equity)

    elif source == "volatility":
        # Multi-source: {"yahoo_finance": {"data": {...}}, "alpha_vantage": {"data": {...}}, "market_volatility_context": {...}}
        yf_data = _get_nested_value(result, "yahoo_finance", "data") or {}
        av_data = _get_nested_value(result, "alpha_vantage", "data") or {}
        market_ctx = result.get("market_volatility_context") or {}

        # VIX from market context
        vix = market_ctx.get("vix") or {}
        if isinstance(vix, dict) and vix.get("value") is not None:
            await emit_metric(progress_callback, source, "VIX", vix["value"])

        # Beta - prefer Yahoo Finance
        beta = yf_data.get("beta") or av_data.get("beta")
        if isinstance(beta, dict) and beta.get("value") is not None:
            await emit_metric(progress_callback, source, "beta", beta["value"])
        elif isinstance(beta, (int, float)):
            await emit_metric(progress_callback, source, "beta", beta)

        # Historical Volatility
        hist_vol = yf_data.get("historical_volatility") or av_data.get("historical_volatility")
        if isinstance(hist_vol, dict) and hist_vol.get("value") is not None:
            await emit_metric(progress_callback, source, "hist_vol", hist_vol["value"])
        elif isinstance(hist_vol, (int, float)):
            await emit_metric(progress_callback, source, "hist_vol", hist_vol)

    elif source == "macro":
        # Multi-source: {"bea_bls": {"data": {...}}, "fred": {"data": {...}}}
        bea_bls = _get_nested_value(result, "bea_bls", "data") or {}
        fred = _get_nested_value(result, "fred", "data") or {}

        # GDP Growth - prefer BEA/BLS
        gdp = bea_bls.get("gdp_growth") or fred.get("gdp_growth") or {}
        if isinstance(gdp, dict) and gdp.get("value") is not None:
            await emit_metric(progress_callback, source, "GDP_growth", gdp["value"])
        elif isinstance(gdp, (int, float)):
            await emit_metric(progress_callback, source, "GDP_growth", gdp)

        # Interest Rate - FRED only
        interest = fred.get("interest_rate") or {}
        if isinstance(interest, dict) and interest.get("value") is not None:
            await emit_metric(progress_callback, source, "interest_rate", interest["value"])
        elif isinstance(interest, (int, float)):
            await emit_metric(progress_callback, source, "interest_rate", interest)

        # Inflation (CPI)
        inflation = bea_bls.get("cpi_inflation") or fred.get("cpi_inflation") or {}
        if isinstance(inflation, dict) and inflation.get("value") is not None:
            await emit_metric(progress_callback, source, "inflation", inflation["value"])
        elif isinstance(inflation, (int, float)):
            await emit_metric(progress_callback, source, "inflation", inflation)

        # Unemployment
        unemployment = bea_bls.get("unemployment") or fred.get("unemployment") or {}
        if isinstance(unemployment, dict) and unemployment.get("value") is not None:
            await emit_metric(progress_callback, source, "unemployment", unemployment["value"])
        elif isinstance(unemployment, (int, float)):
            await emit_metric(progress_callback, source, "unemployment", unemployment)

    elif source == "valuation":
        # Multi-source: {"yahoo_finance": {"data": {...}}, "alpha_vantage": {"data": {...}}}
        yf_data = _get_nested_value(result, "yahoo_finance", "data") or {}
        av_data = _get_nested_value(result, "alpha_vantage", "data") or {}

        # P/E Ratio - prefer Yahoo Finance
        pe_trailing = yf_data.get("trailing_pe") or av_data.get("trailing_pe")
        if pe_trailing is not None:
            await emit_metric(progress_callback, source, "P/E", pe_trailing)

        # P/B Ratio
        pb_ratio = yf_data.get("pb_ratio") or av_data.get("pb_ratio")
        if pb_ratio is not None:
            await emit_metric(progress_callback, source, "P/B", pb_ratio)

        # P/S Ratio
        ps_ratio = yf_data.get("ps_ratio") or av_data.get("ps_ratio")
        if ps_ratio is not None:
            await emit_metric(progress_callback, source, "P/S", ps_ratio)

        # EV/EBITDA
        ev_ebitda = yf_data.get("ev_ebitda") or av_data.get("ev_ebitda")
        if ev_ebitda is not None:
            await emit_metric(progress_callback, source, "EV/EBITDA", ev_ebitda)

    elif source == "news":
        # News-basket returns normalized "items" array
        items = result.get("items") or []
        if items and isinstance(items, list) and len(items) > 0:
            await emit_metric(progress_callback, source, "items_found", len(items))
        else:
            await emit_metric(progress_callback, source, "status", "No recent news found")

    elif source == "sentiment":
        # Sentiment-basket returns raw content (items) without scoring
        # Scoring is applied downstream by analyzer
        items = result.get("items") or []
        if items and isinstance(items, list) and len(items) > 0:
            await emit_metric(progress_callback, source, "items_found", len(items))
        else:
            await emit_metric(progress_callback, source, "status", "No sentiment content found")


def _has_metric(data: dict, field: str) -> bool:
    """Check if metric exists in possibly nested structure."""
    if not isinstance(data, dict):
        return False
    if field in data:
        val = data[field]
        if isinstance(val, dict):
            return val.get("value") is not None
        # Special case for items (list) - news and sentiment
        if isinstance(val, list):
            return len(val) > 0
        return val is not None
    # Check common nested paths
    for key in ["data", "metrics", "sec_edgar", "yahoo_finance"]:
        if key in data and isinstance(data[key], dict):
            if field in data[key]:
                return True
    return False


def _calculate_completeness(metrics: dict, sources_available: list) -> dict:
    """Calculate completeness score and identify missing data."""
    required = {
        "fundamentals": ["revenue", "net_income", "eps", "debt_to_equity"],
        "valuation": ["trailing_pe", "pb_ratio", "ps_ratio"],
        "volatility": ["beta", "vix"],
        "macro": ["gdp_growth", "interest_rate", "cpi_inflation"],
        "news": ["items"],
        "sentiment": ["items"]
    }

    total = 0
    found = 0
    missing = {}

    for source, fields in required.items():
        source_data = metrics.get(source, {})
        missing[source] = []
        for field in fields:
            total += 1
            if _has_metric(source_data, field):
                found += 1
            else:
                missing[source].append(field)

    return {
        "completeness_pct": round(found / total * 100, 1) if total > 0 else 0,
        "metrics_found": found,
        "metrics_total": total,
        "missing": {k: v for k, v in missing.items() if v}
    }


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


def _sort_and_limit_news(news_data: dict, limit: int = 10) -> dict:
    """Sort news items by date (most recent first) and limit to top N."""
    if not news_data or "items" not in news_data:
        return news_data

    items = news_data.get("items", [])

    # Sort by datetime descending (most recent first)
    def get_date(item):
        date_str = item.get("datetime") or ""
        return date_str if date_str else "1970-01-01"

    sorted_items = sorted(items, key=get_date, reverse=True)

    # Limit to top N
    news_data["items"] = sorted_items[:limit]
    news_data["total_items"] = len(items)
    news_data["showing"] = min(limit, len(items))

    return news_data


def _sort_and_limit_sentiment(sentiment_data: dict, limit: int = 10) -> dict:
    """Sort sentiment items by date (most recent first) and limit to top N."""
    if not sentiment_data or "items" not in sentiment_data:
        return sentiment_data

    items = sentiment_data.get("items", [])

    # Sort by datetime descending (most recent first)
    def get_date(item):
        return item.get("datetime") or "1970-01-01"

    sorted_items = sorted(items, key=get_date, reverse=True)

    # Limit to top N
    sentiment_data["items"] = sorted_items[:limit]
    sentiment_data["total_items"] = len(items)
    sentiment_data["showing"] = min(limit, len(items))

    return sentiment_data


def _add_conflict_markers(fundamentals_all: dict, valuation_all: dict) -> dict:
    """
    Add conflict resolution markers to multi-source data.
    Primary sources: SEC EDGAR (fundamentals), Yahoo Finance (valuation)
    """
    conflict_resolution = {
        "fundamentals": {
            "primary_source": "SEC EDGAR XBRL",
            "secondary_source": "Yahoo Finance",
            "conflicts": []
        },
        "valuation": {
            "primary_source": "Yahoo Finance",
            "secondary_source": "Alpha Vantage",
            "conflicts": []
        }
    }

    # Check fundamentals for conflicts
    if fundamentals_all and "sec_edgar" in fundamentals_all and "yahoo_finance" in fundamentals_all:
        sec_data = fundamentals_all.get("sec_edgar", {}).get("data", {})
        yf_data = fundamentals_all.get("yahoo_finance", {}).get("data", {})

        for metric in ["revenue", "net_income", "free_cash_flow"]:
            sec_val = sec_data.get(metric, {})
            yf_val = yf_data.get(metric, {})

            if isinstance(sec_val, dict):
                sec_val = sec_val.get("value")
            if isinstance(yf_val, dict):
                yf_val = yf_val.get("value")
                if isinstance(yf_val, dict):
                    yf_val = yf_val.get("value")

            if sec_val and yf_val and sec_val != yf_val:
                conflict_resolution["fundamentals"]["conflicts"].append({
                    "metric": metric,
                    "primary_value": sec_val,
                    "secondary_value": yf_val,
                    "used": "primary"
                })

    # Check valuation for conflicts
    if valuation_all and "yahoo_finance" in valuation_all and "alpha_vantage" in valuation_all:
        yf_data = valuation_all.get("yahoo_finance", {}).get("data", {})
        av_data = valuation_all.get("alpha_vantage", {}).get("data", {})

        for metric in ["trailing_pe", "forward_pe", "pb_ratio", "ps_ratio"]:
            yf_val = yf_data.get(metric)
            av_val = av_data.get(metric)

            if yf_val and av_val and abs(yf_val - av_val) > 0.5:
                conflict_resolution["valuation"]["conflicts"].append({
                    "metric": metric,
                    "primary_value": yf_val,
                    "secondary_value": av_val,
                    "used": "primary"
                })

    return conflict_resolution


async def fetch_all_research_data(
    ticker: str,
    company_name: str,
    progress_callback: Optional[Callable] = None
) -> dict:
    """
    Fetch data from 6 MCP servers SEQUENTIALLY using TRUE MCP protocol.
    Only calls multi-source (_all) versions to avoid duplicate API calls.

    Order: fundamentals -> valuation -> volatility -> macro -> news -> sentiment

    Args:
        ticker: Stock ticker symbol
        company_name: Company name
        progress_callback: Optional callback for granular metric events

    Returns aggregated results with sources_available, sources_failed, and aggregated_swot.
    """
    logger.info(f"Fetching from MCP servers for {ticker} ({company_name})...")

    # Sequential order: critical data first
    mcp_sequence = [
        ("fundamentals", lambda: call_fundamentals_all_sources_mcp(ticker)),
        ("valuation", lambda: call_valuation_all_sources_mcp(ticker)),
        ("volatility", lambda: call_volatility_all_sources_mcp(ticker)),
        ("macro", lambda: call_macro_all_sources_mcp()),
        ("news", lambda: call_news_mcp(ticker, company_name)),
        ("sentiment", lambda: call_sentiment_mcp(ticker, company_name)),
    ]

    # Normalizers to convert MCP schemas to analyzer-expected format
    normalizers = {
        "fundamentals": _normalize_fundamentals,
        "valuation": _normalize_valuation,
        "volatility": _normalize_volatility,
        "macro": _normalize_macro,
    }

    metrics = {}
    sources_available = []
    sources_failed = []

    # Sequential execution - one at a time
    for name, mcp_func in mcp_sequence:
        logger.info(f"Fetching {name}...")

        try:
            result = await mcp_func()

            if isinstance(result, dict) and "error" in result:
                # First attempt failed, retry once
                logger.warning(f"MCP {name} error, retrying: {result.get('error', 'Unknown')[:50]}")
                result = await mcp_func()

                if isinstance(result, dict) and "error" in result:
                    sources_failed.append(name)
                    metrics[name] = {**result, "retried": True}
                    logger.warning(f"MCP {name} failed after retry: {result.get('error')}")
                else:
                    # Apply normalizer if available
                    if name in normalizers:
                        result = normalizers[name](result)
                    sources_available.append(name)
                    metrics[name] = result
                    logger.info(f"MCP {name} succeeded on retry")
                    # Emit metrics for real-time streaming to frontend
                    await _extract_and_emit_metrics(name, result, progress_callback)
            else:
                # Apply normalizer if available
                if name in normalizers:
                    result = normalizers[name](result)
                sources_available.append(name)
                metrics[name] = result
                logger.info(f"MCP {name} fetched successfully")
                # Emit metrics for real-time streaming to frontend
                await _extract_and_emit_metrics(name, result, progress_callback)

        except Exception as e:
            # First attempt exception, retry once
            logger.warning(f"MCP {name} exception, retrying: {e}")
            try:
                result = await mcp_func()
                if isinstance(result, dict) and "error" not in result:
                    # Apply normalizer if available
                    if name in normalizers:
                        result = normalizers[name](result)
                    sources_available.append(name)
                    metrics[name] = result
                    logger.info(f"MCP {name} succeeded on retry")
                    # Emit metrics for real-time streaming to frontend
                    await _extract_and_emit_metrics(name, result, progress_callback)
                else:
                    sources_failed.append(name)
                    metrics[name] = {"error": str(result.get("error", e)), "retried": True}
                    logger.warning(f"MCP {name} failed after retry")
            except Exception as e2:
                sources_failed.append(name)
                metrics[name] = {"error": str(e2), "retried": True}
                logger.warning(f"MCP {name} failed after retry: {e2}")

    # Apply sorting and limiting to news (top 10, most recent first)
    if "news" in metrics and "error" not in metrics.get("news", {}):
        metrics["news"] = _sort_and_limit_news(metrics["news"], limit=10)

    # Apply sorting and limiting to sentiment (top 10 articles/posts, most recent first)
    if "sentiment" in metrics and "error" not in metrics.get("sentiment", {}):
        metrics["sentiment"] = _sort_and_limit_sentiment(metrics["sentiment"], limit=10)

    # Get multi-source data (now stored directly under source name)
    fundamentals_data = metrics.get("fundamentals", {})
    valuation_data = metrics.get("valuation", {})
    macro_data = metrics.get("macro", {})
    volatility_data = metrics.get("volatility", {})

    # Add conflict resolution markers
    conflict_resolution = _add_conflict_markers(fundamentals_data, valuation_data)

    # Build aggregated SWOT from primary source data
    aggregated_swot = _aggregate_swot(metrics, sources_available)

    # Calculate completeness score
    completeness = _calculate_completeness(metrics, sources_available)

    # Final data package - shared with analyzer only after all collection complete
    data = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "sources_available": sources_available,
        "sources_failed": sources_failed,
        "metrics": metrics,
        "multi_source": {
            "fundamentals_all": fundamentals_data,
            "valuation_all": valuation_data,
            "macro_all": macro_data,
            "volatility_all": volatility_data,
        },
        "conflict_resolution": conflict_resolution,
        "aggregated_swot": aggregated_swot,
        "completeness": completeness,
        "generated_at": datetime.now().isoformat()
    }

    logger.info(f"Research complete: {len(sources_available)} sources, {len(sources_failed)} failed, {completeness['completeness_pct']}% complete")

    return data
