"""
Financials Basket HTTP Server

FastAPI wrapper around the microservices architecture for HTTP-based load balancing.
Runs as a persistent service instead of spawning new processes per request.

Usage:
    uvicorn http_server:app --host 0.0.0.0 --port 8001

Multiple instances can run on different ports behind nginx load balancer.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.orchestrator import get_orchestrator_service
from config import TOOL_TIMEOUT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("financials-http")

# Instance identification
INSTANCE_ID = os.getenv("INSTANCE_ID", f"financials-{os.getpid()}")

# FastAPI app
app = FastAPI(
    title="Financials Basket HTTP API",
    description="HTTP interface for SEC EDGAR and Yahoo Finance data with load balancing support",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator service (warm on startup)
orchestrator = get_orchestrator_service()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ToolRequest(BaseModel):
    """Request body for tool calls."""
    ticker: Optional[str] = None
    limit: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    instance: str
    uptime_seconds: float
    cache_stats: Dict[str, Any]


# Track startup time
_startup_time = datetime.now()


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for nginx load balancer.

    Returns instance status and cache statistics.
    """
    uptime = (datetime.now() - _startup_time).total_seconds()
    status = orchestrator.get_status()

    return HealthResponse(
        status="ok",
        instance=INSTANCE_ID,
        uptime_seconds=uptime,
        cache_stats=status.get("cache", {}),
    )


@app.get("/status")
async def detailed_status():
    """
    Detailed status including circuit breaker and rate limiter state.
    """
    status = orchestrator.get_status()
    return {
        "instance": INSTANCE_ID,
        "uptime_seconds": (datetime.now() - _startup_time).total_seconds(),
        **status,
    }


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: ToolRequest):
    """
    Execute a tool by name.

    Supported tools:
    - get_company_info
    - get_financials
    - get_debt_metrics
    - get_cash_flow
    - get_sec_fundamentals
    - get_all_sources_fundamentals
    - get_material_events
    - get_ownership_filings
    - get_going_concern
    """
    logger.info(f"[{INSTANCE_ID}] Tool call: {tool_name} ticker={request.ticker}")

    # Build arguments
    arguments = {}
    if request.ticker:
        arguments["ticker"] = request.ticker.upper()
    if request.limit is not None:
        arguments["limit"] = request.limit

    # Validate required arguments
    tools_requiring_ticker = {
        "get_company_info",
        "get_financials",
        "get_debt_metrics",
        "get_cash_flow",
        "get_sec_fundamentals",
        "get_all_sources_fundamentals",
        "get_material_events",
        "get_ownership_filings",
        "get_going_concern",
    }

    if tool_name in tools_requiring_ticker and not arguments.get("ticker"):
        raise HTTPException(status_code=400, detail="ticker is required")

    try:
        # Execute via orchestrator with timeout
        result = await asyncio.wait_for(
            orchestrator.execute_tool(tool_name, arguments),
            timeout=TOOL_TIMEOUT
        )

        # Add instance metadata
        if isinstance(result, dict):
            result["_instance"] = INSTANCE_ID

        return result

    except asyncio.TimeoutError:
        logger.error(f"[{INSTANCE_ID}] Tool {tool_name} timed out")
        raise HTTPException(
            status_code=504,
            detail=f"Tool execution timed out after {TOOL_TIMEOUT} seconds"
        )
    except Exception as e:
        logger.error(f"[{INSTANCE_ID}] Tool {tool_name} error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CONVENIENCE ENDPOINTS (Direct tool access)
# =============================================================================

@app.get("/company/{ticker}")
async def get_company_info(ticker: str):
    """Get company information for a ticker."""
    return await call_tool("get_company_info", ToolRequest(ticker=ticker))


@app.get("/financials/{ticker}")
async def get_financials(ticker: str):
    """Get financial metrics for a ticker."""
    return await call_tool("get_financials", ToolRequest(ticker=ticker))


@app.get("/fundamentals/{ticker}")
async def get_fundamentals(ticker: str):
    """Get full SEC fundamentals basket with SWOT."""
    return await call_tool("get_sec_fundamentals", ToolRequest(ticker=ticker))


@app.get("/all-sources/{ticker}")
async def get_all_sources(ticker: str):
    """Get financials from all sources (SEC EDGAR + Yahoo Finance)."""
    return await call_tool("get_all_sources_fundamentals", ToolRequest(ticker=ticker))


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"[{INSTANCE_ID}] Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "instance": INSTANCE_ID,
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
        }
    )


# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Warm up services on startup."""
    logger.info(f"[{INSTANCE_ID}] Starting HTTP server...")
    logger.info(f"[{INSTANCE_ID}] Orchestrator initialized: {orchestrator}")
    logger.info(f"[{INSTANCE_ID}] Ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info(f"[{INSTANCE_ID}] Shutting down...")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("HTTP_PORT", "8001"))
    host = os.getenv("HTTP_HOST", "0.0.0.0")

    uvicorn.run(app, host=host, port=port)
