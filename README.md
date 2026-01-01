---
title: Researcher Agent
emoji: 🔬
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Research Service

Financial research service implementing Google's A2A (Agent-to-Agent) protocol. Uses TRUE MCP protocol (subprocess + JSON-RPC) to fetch data from 6 MCP servers and returns aggregated research data for SWOT analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Research Service                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  A2A Server (FastAPI + JSON-RPC 2.0)                      │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  MCP Client (TRUE MCP: subprocess + JSON-RPC)       │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │  │
│  │  │  │Financials│ │Volatility│ │  Macro   │            │  │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘            │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │  │
│  │  │  │Valuation │ │   News   │ │Sentiment │            │  │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘            │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## TRUE MCP Protocol

This service uses TRUE MCP protocol with proper handshake:

1. Send `initialize` request (id=1)
2. Receive initialization response
3. Send `notifications/initialized` notification
4. Send `tools/call` request (id=2)
5. Parse JSON-RPC response

Each MCP server is called via subprocess + stdio, following the official MCP specification.

## A2A Protocol

This agent implements the [Google A2A Protocol](https://github.com/google-a2a/A2A) using JSON-RPC 2.0 over HTTP.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | POST | JSON-RPC 2.0 endpoint |
| `/.well-known/agent.json` | GET | Agent card |
| `/health` | GET | Health check |

### JSON-RPC Methods

#### `message/send`
Start a new research task.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "message/send",
  "params": {
    "message": {
      "parts": [{"type": "text", "text": "Research Tesla"}]
    }
  }
}
```

#### `tasks/get`
Get task status and results. Includes `partial_metrics` during WORKING status for real-time streaming.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tasks/get",
  "params": {"taskId": "abc-123-def"}
}
```

#### `tasks/cancel`
Cancel a running task.

## Data Sources

| MCP Server | Data Source | Metrics |
|------------|-------------|---------|
| Financials | SEC EDGAR | Revenue, margins, debt, EPS |
| Volatility | Yahoo Finance, FRED | Beta, VIX, historical volatility |
| Macro | FRED | GDP growth, interest rates, inflation, unemployment |
| Valuation | Yahoo Finance | P/E, P/B, P/S, EV/EBITDA, PEG |
| News | Tavily | Recent news articles |
| Sentiment | Finnhub, Reddit | Composite sentiment score |

## Environment Variables

```bash
FRED_API_KEY=xxx        # For macro indicators
FINNHUB_API_KEY=xxx     # For sentiment analysis
TAVILY_API_KEY=xxx      # For news search
METRIC_DELAY_MS=300     # Delay between metric emissions (ms)
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Server runs on `http://localhost:7860`

## Usage from Main SWOT Agent

The main SWOT Analysis Agent connects to this server via A2A protocol:

```python
# In main agent (Research Gateway)
A2A_RESEARCHER_URL = "https://vn6295337-researcher-agent.hf.space"

# Send research request
response = requests.post(A2A_RESEARCHER_URL, json={
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/send",
    "params": {"message": {"parts": [{"type": "text", "text": "Research TSLA Tesla"}]}}
})
```

## License

MIT
