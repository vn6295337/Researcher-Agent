# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Financial research microservice implementing Google A2A (Agent-to-Agent) protocol. Fetches data from 6 MCP (Model Context Protocol) servers via subprocess + JSON-RPC and returns aggregated research data for SWOT analysis. Deployed on HuggingFace Spaces.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the A2A server (port 7860)
python app.py

# E2E test for all 6 MCP servers
python tests/test_mcp_e2e.py [TICKER] [COMPANY_NAME]
# Example: python tests/test_mcp_e2e.py AAPL "Apple Inc"

# Test individual MCP servers
python mcp-servers/fundamentals-basket/test_fetchers.py AAPL
python mcp-servers/valuation-basket/test_fetchers.py AAPL
python mcp-servers/volatility-basket/test_fetchers.py AAPL
python mcp-servers/macro-basket/test_fetchers.py
python mcp-servers/news-basket/test_fetchers.py AAPL
python mcp-servers/sentiment-basket/test_fetchers.py AAPL

# Stress tests
python scripts/mcp_stress_test.py
```

## Architecture

```
app.py (FastAPI A2A Server)
    │
    └── mcp_client.py (MCP Orchestrator)
            │
            ├── fundamentals-basket/  → SEC EDGAR (revenue, debt, EPS)
            ├── valuation-basket/     → Yahoo Finance (P/E, P/B, P/S)
            ├── volatility-basket/    → Yahoo Finance, FRED (beta, VIX)
            ├── macro-basket/         → FRED, BEA, BLS (GDP, CPI, rates)
            ├── news-basket/          → Tavily, NYT, NewsAPI
            └── sentiment-basket/     → Finnhub, Reddit (sentiment scores)
```

**Key patterns:**
- A2A protocol: JSON-RPC 2.0 over HTTP (methods: `message/send`, `tasks/get`, `tasks/cancel`)
- TRUE MCP: Subprocess spawning with stdio JSON-RPC handshake (initialize → initialized → tools/call)
- Sequential execution: MCP servers called one at a time for priority ordering
- Partial metrics streaming: `partial_metrics` field in task response for real-time UI updates
- HTTP fallback: Optional load-balanced HTTP mode for fundamentals (`USE_HTTP_FINANCIALS=true`)

## MCP Server Structure

Each MCP server in `mcp-servers/<name>-basket/` follows this pattern:
- `server.py` - MCP server entry point (subprocess target)
- `fetchers.py` - API data fetching functions
- `normalizer.py` - Schema normalization to common format
- `test_fetchers.py` - Standalone test script

## Environment Variables

Required API keys in `.env`:
```bash
FRED_API_KEY=...        # Macroeconomic data
FINNHUB_API_KEY=...     # Sentiment analysis
TAVILY_API_KEY=...      # News search
BEA_API_KEY=...         # GDP data
BLS_API_KEY=...         # CPI, unemployment (optional)
NYT_API_KEY=...         # New York Times (optional)
NEWSAPI_API_KEY=...     # NewsAPI (optional)
```

Configuration:
```bash
METRIC_DELAY_MS=0           # Delay between metric emissions (0 for speed)
USE_HTTP_FINANCIALS=false   # Use HTTP instead of subprocess for fundamentals
HTTP_TIMEOUT=90.0           # HTTP request timeout
```

## Data Flow

1. Caller sends `message/send` with "Research {TICKER} {COMPANY}"
2. Server creates task, runs `fetch_all_research_data()` in background
3. MCP orchestrator calls 6 servers sequentially, emits partial metrics
4. Caller polls `tasks/get` for status and `partial_metrics`
5. On completion, full aggregated data in `artifacts[0].data`

## Key Files

- `app.py` - A2A server with task management
- `mcp_client.py` - MCP orchestration, subprocess spawning, HTTP fallback
- `configs/output_schemas.py` - Output format definitions
- `utils/ticker_lookup.py` - Company name to ticker resolution
- `docs/metrics_schema_human_readable.md` - Complete output schema documentation
