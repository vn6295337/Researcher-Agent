"""
Research Service - A2A Server

Standalone research agent implementing Google A2A protocol.
Fetches data from 6 MCP servers using TRUE MCP protocol (subprocess + JSON-RPC)
and returns aggregated research data.

Deployed on HuggingFace Spaces as a separate A2A agent.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# TRUE MCP protocol client (subprocess + JSON-RPC)
from mcp_client import fetch_all_research_data

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("research-service")

# FastAPI app
app = FastAPI(
    title="Research Service",
    description="Financial research service for SWOT analysis - fetches data from 6 MCP servers using TRUE MCP protocol",
    version="1.1.1"
)

# CORS for cross-origin requests from main SWOT app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server configuration
A2A_SERVER_URL = os.getenv("A2A_SERVER_URL", "https://vn6295337-researcher-agent.hf.space")


# ============================================================
# A2A PROTOCOL TYPES
# ============================================================

class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class MetricEntry(BaseModel):
    """Granular metric entry for partial results streaming."""
    source: str
    metric: str
    value: Any
    timestamp: str
    # Temporal fields for financial data
    end_date: Optional[str] = None      # "2023-09-30"
    fiscal_year: Optional[int] = None   # 2023
    form: Optional[str] = None          # "10-K" or "10-Q"


class Task(BaseModel):
    id: str
    status: TaskStatus
    message: Optional[Dict[str, Any]] = None
    artifacts: Optional[list] = None
    partial_metrics: Optional[List[MetricEntry]] = None  # For streaming during WORKING status
    error: Optional[str] = None
    created_at: str
    updated_at: str


# In-memory task store
TASK_STORE: Dict[str, Task] = {}


# ============================================================
# AGENT CARD
# ============================================================

AGENT_CARD = {
    "name": "research-service",
    "version": "1.1.1",
    "description": "Financial research service that collects data from 6 MCP servers using TRUE MCP protocol (subprocess + JSON-RPC) for SWOT analysis.",
    "url": A2A_SERVER_URL,
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False,
        "partialResults": True  # Supports partial_metrics during WORKING status
    },
    "authentication": {
        "schemes": []
    },
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["data"],
    "skills": [
        {
            "id": "research-company",
            "name": "Company Research",
            "description": "Fetch comprehensive financial data for a company from SEC EDGAR, Yahoo Finance, FRED, Tavily News, and Finnhub Sentiment",
            "inputModes": ["text"],
            "outputModes": ["data"],
            "examples": [
                {"input": "Research Tesla", "output": "Aggregated financial data for TSLA"},
                {"input": "Research AAPL Apple Inc", "output": "Financial data for Apple"}
            ]
        }
    ],
    "dataSources": [
        "SEC EDGAR (financials, filings)",
        "Yahoo Finance (valuation, volatility)",
        "FRED (macro indicators)",
        "Tavily (news search)",
        "Finnhub (sentiment)",
        "Reddit (sentiment)"
    ]
}


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Return the A2A agent card."""
    return JSONResponse(content=AGENT_CARD)


# ============================================================
# JSON-RPC HANDLERS
# ============================================================

def create_jsonrpc_response(id: Any, result: Any = None, error: Any = None) -> dict:
    """Create a JSON-RPC 2.0 response."""
    response = {"jsonrpc": "2.0", "id": id}
    if error:
        response["error"] = error
    else:
        response["result"] = result
    return response


def parse_research_request(message: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Parse company name and ticker from message.

    Expects message format:
    {
        "parts": [{"type": "text", "text": "Research Tesla"}]
    }
    """
    parts = message.get("parts", [])
    if not parts:
        return None, None

    text = ""
    for part in parts:
        if part.get("type") == "text":
            text = part.get("text", "")
            break

    # Parse "Research <company>" format
    text = text.strip()
    if text.lower().startswith("research "):
        text = text[9:].strip()

    # Check if format is "TICKER CompanyName" or just "CompanyName"
    words = text.split()
    if len(words) >= 2 and words[0].isupper() and len(words[0]) <= 5:
        ticker = words[0]
        company_name = " ".join(words[1:])
    else:
        # Use ticker lookup
        from utils.ticker_lookup import get_ticker, normalize_company_name
        company_name = normalize_company_name(text)
        ticker = get_ticker(text)
        if not ticker:
            ticker = text.upper().replace(" ", "")[:5]

    # Clean company name (strip "- Common Stock", "Inc.", etc.)
    from configs.company_name_filters import clean_company_name
    company_name = clean_company_name(company_name)

    return ticker, company_name


async def handle_message_send(params: dict, request_id: Any) -> dict:
    """
    Handle message/send JSON-RPC method.

    Creates a new task and starts processing in background.
    """
    message = params.get("message", {})

    # Parse request
    ticker, company_name = parse_research_request(message)

    if not ticker:
        return create_jsonrpc_response(
            request_id,
            error={"code": -32602, "message": "Invalid params: could not parse company/ticker"}
        )

    # Create task
    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    task = Task(
        id=task_id,
        status=TaskStatus.SUBMITTED,
        message=message,
        partial_metrics=[],
        created_at=now,
        updated_at=now
    )
    TASK_STORE[task_id] = task

    # Start background processing
    asyncio.create_task(process_research_task(task_id, ticker, company_name))

    logger.info(f"Created task {task_id} for {company_name} ({ticker})")

    return create_jsonrpc_response(request_id, result={
        "task": {
            "id": task_id,
            "status": task.status.value
        }
    })


def create_progress_callback(task_id: str):
    """Create a progress callback that receives structured metric payloads."""
    def callback(payload: dict):
        task = TASK_STORE.get(task_id)
        if task and task.status == TaskStatus.WORKING:
            # Extract fields from structured payload
            source = payload.get("source", "unknown")
            metric = payload.get("metric", "unknown")
            value = payload.get("value")
            end_date = payload.get("end_date")
            fiscal_year = payload.get("fiscal_year")
            form = payload.get("form")

            entry = MetricEntry(
                source=source,
                metric=metric,
                value=value,
                timestamp=datetime.now().isoformat(),
                end_date=end_date,
                fiscal_year=fiscal_year,
                form=form
            )
            if task.partial_metrics is None:
                task.partial_metrics = []
            task.partial_metrics.append(entry)
            task.updated_at = datetime.now().isoformat()
            temporal_info = f" ({form} {fiscal_year})" if fiscal_year else ""
            logger.info(f"Task {task_id}: [{source}] {metric} = {value}{temporal_info}")
    return callback


async def process_research_task(task_id: str, ticker: str, company_name: str):
    """Background task processor with partial metrics streaming."""
    task = TASK_STORE.get(task_id)
    if not task:
        return

    # Update to working status
    task.status = TaskStatus.WORKING
    task.updated_at = datetime.now().isoformat()

    try:
        # Create progress callback for partial metrics
        progress_callback = create_progress_callback(task_id)

        # Fetch research data with progress streaming
        logger.info(f"Task {task_id}: Starting research for {company_name} ({ticker})")
        result = await fetch_all_research_data(ticker, company_name, progress_callback)

        # Create artifact
        task.artifacts = [{
            "type": "data",
            "mimeType": "application/json",
            "data": result
        }]
        task.status = TaskStatus.COMPLETED
        logger.info(f"Task {task_id}: Research completed - {len(result.get('sources_available', []))} sources")

    except Exception as e:
        logger.error(f"Task {task_id}: Research failed - {e}")
        task.status = TaskStatus.FAILED
        task.error = str(e)

    task.updated_at = datetime.now().isoformat()


async def handle_tasks_get(params: dict, request_id: Any) -> dict:
    """
    Handle tasks/get JSON-RPC method.

    Returns the status, partial_metrics (if WORKING), and result (if COMPLETED).
    """
    task_id = params.get("taskId") or params.get("id")

    if not task_id:
        return create_jsonrpc_response(
            request_id,
            error={"code": -32602, "message": "Invalid params: taskId required"}
        )

    task = TASK_STORE.get(task_id)

    if not task:
        return create_jsonrpc_response(
            request_id,
            error={"code": -32001, "message": f"Task not found: {task_id}"}
        )

    result = {
        "task": {
            "id": task.id,
            "status": task.status.value,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at
        }
    }

    # Include partial_metrics for WORKING and COMPLETED (ensures final sources aren't missed)
    if task.partial_metrics and task.status in (TaskStatus.WORKING, TaskStatus.COMPLETED):
        result["task"]["partial_metrics"] = [m.model_dump() for m in task.partial_metrics]

    if task.status == TaskStatus.COMPLETED and task.artifacts:
        result["task"]["artifacts"] = task.artifacts

    if task.status == TaskStatus.FAILED and task.error:
        result["task"]["error"] = {"message": task.error}

    return create_jsonrpc_response(request_id, result=result)


async def handle_tasks_cancel(params: dict, request_id: Any) -> dict:
    """Handle tasks/cancel JSON-RPC method."""
    task_id = params.get("taskId") or params.get("id")

    if not task_id:
        return create_jsonrpc_response(
            request_id,
            error={"code": -32602, "message": "Invalid params: taskId required"}
        )

    task = TASK_STORE.get(task_id)

    if not task:
        return create_jsonrpc_response(
            request_id,
            error={"code": -32001, "message": f"Task not found: {task_id}"}
        )

    if task.status in [TaskStatus.SUBMITTED, TaskStatus.WORKING]:
        task.status = TaskStatus.CANCELED
        task.updated_at = datetime.now().isoformat()

    return create_jsonrpc_response(request_id, result={
        "task": {"id": task.id, "status": task.status.value}
    })


# ============================================================
# MAIN ENDPOINT
# ============================================================

@app.post("/")
async def handle_jsonrpc(request: Request):
    """
    Main JSON-RPC 2.0 endpoint for A2A protocol.

    Supported methods:
    - message/send: Start a new research task
    - tasks/get: Get task status, partial_metrics, and result
    - tasks/cancel: Cancel a running task
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content=create_jsonrpc_response(
            None,
            error={"code": -32700, "message": "Parse error"}
        ))

    # Validate JSON-RPC request
    if body.get("jsonrpc") != "2.0":
        return JSONResponse(content=create_jsonrpc_response(
            body.get("id"),
            error={"code": -32600, "message": "Invalid Request: must be JSON-RPC 2.0"}
        ))

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    # Route to handler
    if method == "message/send":
        response = await handle_message_send(params, request_id)
    elif method == "tasks/get":
        response = await handle_tasks_get(params, request_id)
    elif method == "tasks/cancel":
        response = await handle_tasks_cancel(params, request_id)
    else:
        response = create_jsonrpc_response(
            request_id,
            error={"code": -32601, "message": f"Method not found: {method}"}
        )

    return JSONResponse(content=response)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": "research-service",
        "version": "1.1.1",
        "protocol": "TRUE MCP (subprocess + JSON-RPC)",
        "tasks_in_memory": len(TASK_STORE),
        "capabilities": ["partial_metrics_streaming"]
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Research Service",
        "version": "1.1.1",
        "protocol": "A2A (JSON-RPC 2.0) + TRUE MCP (subprocess)",
        "endpoints": {
            "POST /": "JSON-RPC endpoint (message/send, tasks/get, tasks/cancel)",
            "GET /.well-known/agent.json": "Agent card",
            "GET /health": "Health check"
        }
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7860"))  # HuggingFace Spaces default
    logger.info(f"Starting Research Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
