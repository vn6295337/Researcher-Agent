# Researcher-Agent Data Flow

## Request Flow

```
Frontend/Caller
      │
      │  POST / (JSON-RPC: message/send)
      │
      │  Example Request:
      │  {
      │    "jsonrpc": "2.0",
      │    "method": "message/send",
      │    "params": {"message": {"content": "Research AAPL"}},
      │    "id": 1
      │  }
      ▼
┌──────────────────┐
│     app.py       │  A2A Server (port 7860)
└────────┬─────────┘
         │
         │  Extracts: ticker="AAPL", company_name="Apple Inc"
         │  Spawns background task, returns task_id
         │
         │  Example Response:
         │  {"jsonrpc": "2.0", "result": {"task": {"id": "task-123", "status": "working"}}, "id": 1}
         ▼
┌──────────────────┐
│  mcp_client.py   │  Orchestrator
└────────┬─────────┘
         │
         │  Spawns each MCP server as subprocess
         │  Sends JSON-RPC over stdio
         │
         │  Example MCP Request:
         │  {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_all_sources_fundamentals", "arguments": {"ticker": "AAPL"}}, "id": 2}
         ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                      MCP SERVERS                                          │
│                                                                                           │
│  1. fundamentals-basket/server.py                                                           │
│        └─► SEC EDGAR ──► {"revenue": {"value": 416161000000, "fiscal_year": 2025}}        │
│        └─► Yahoo Finance (fallback)                                                       │
│                                                                                           │
│  2. valuation-basket/server.py                                                            │
│        └─► Yahoo Finance ──► {"trailing_pe": 34.72, "pb_ratio": 52.17}                    │
│        └─► Alpha Vantage (fallback)                                                       │
│                                                                                           │
│  3. volatility-basket/server.py                                                           │
│        └─► FRED ──► {"vix": {"value": 15.45}, "vxn": {"value": 20.15}}                    │
│        └─► Yahoo Finance ──► {"beta": 1.29, "historical_volatility": 0.12}                │
│                                                                                           │
│  4. macro-basket/server.py                                                                │
│        └─► BEA ──► {"gdp_growth": {"value": 4.3, "date": "Q3 2025"}}                      │
│        └─► BLS ──► {"cpi": 2.74, "unemployment": 4.4}                                     │
│        └─► FRED ──► {"interest_rate": 3.72}                                               │
│                                                                                           │
│  5. news-basket/server.py                                                                 │
│        └─► Tavily + NYT + NewsAPI ──► {"items": [{"title": "...", "url": "..."}]}         │
│                                                                                           │
│  6. sentiment-basket/server.py                                                            │
│        └─► Finnhub ──► {"items": [{"title": "...", "url": "..."}]}                        │
│        └─► Reddit ──► {"items": [{"title": "...", "url": "..."}]}                         │
└──────────────────────────────────────────────────────────────────────────────────────────┘
         │
         │  Example MCP Response:
         │  {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": "{...}"}]}, "id": 2}
         ▼
┌──────────────────┐
│  mcp_client.py   │  Aggregates all sources
└────────┬─────────┘
         │
         │  Merges 6 responses into single payload
         │
         │  Completeness: checks required vs missing
         │    required = {
         │      "financials": ["revenue", "net_income", "eps", "debt_to_equity"],
         │      "valuation": ["trailing_pe", "pb_ratio", "ps_ratio"],
         │      "volatility": ["beta", "vix"],
         │      "macro": ["gdp_growth", "interest_rate", "cpi_inflation"],
         │      "news": ["items"],
         │      "sentiment": ["items"]
         │    }
         │    missing = {"volatility": ["implied_volatility"]}
         │    found: 19, total: 20
         │
         │  Conflict Resolution: compares primary vs secondary source values
         │    financials: SEC EDGAR (primary) vs Yahoo Finance (secondary)
         │    valuation:  Yahoo Finance (primary) vs Alpha Vantage (secondary)
         │    → if values differ, marks conflict and uses primary
         │    → example: {"metric": "revenue", "primary_value": 416B, "secondary_value": 415B, "used": "primary"}
         │
         │  Example Aggregated:
         │  {"ticker": "AAPL", "metrics": {...}, "multi_source": {...}, "completeness": {"pct": 95}}
         ▼
┌──────────────────┐
│     app.py       │  Stores as task artifact
└────────┬─────────┘
         │
         │  Updates task status: "working" → "completed"
         │  Stores result in artifacts[]
         │
         │  Example Final Response (tasks/get):
         │  {"jsonrpc": "2.0", "result": {"task": {"id": "task-123", "status": "completed", "artifacts": [{...}]}}, "id": 3}
         ▼
Frontend/Caller
```

---

## Output Structure

```python
{
  "ticker": "AAPL",
  "company_name": "Apple Inc",
  "sources_available": ["financials", "valuation", ...],
  "sources_failed": [],
  "metrics": {
    "fundamentals": {...},
    "valuation": {...},
    "volatility": {...},
    "macro": {...},
    "news": {...},
    "sentiment": {...}
  },
  "multi_source": {
    "fundamentals_all": {...},
    "valuation_all": {...},
    "volatility_all": {...},
    "macro_all": {...}
  },
  "completeness": {
    "completeness_pct": 95.0,
    "metrics_found": 19,
    "metrics_total": 20,
    "missing": ["implied_volatility"]
  },
  "generated_at": "2026-01-10T..."
}
```
