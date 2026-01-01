# Volatility Basket MCP Server - Technical Documentation

MCP server implementation for volatility metrics aggregation.

## Installation

```bash
cd mcp-servers/volatility-basket
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Add to `~/.env`:

```bash
# Required - FRED API for authoritative VIX data
FRED_API_KEY=your_key_here

# Optional - Alpha Vantage for implied volatility
ALPHA_VANTAGE_API_KEY=your_key_here
```

Get free keys:
- FRED: https://fred.stlouisfed.org/docs/api/api_key.html
- Alpha Vantage: https://www.alphavantage.co/support/#api-key

## MCP Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `get_vix` | None | VIX level, interpretation, SWOT category |
| `get_beta` | `ticker: string` | Beta coefficient vs S&P 500 |
| `get_historical_volatility` | `ticker: string`, `period_days: int` | Annualized HV % |
| `get_implied_volatility` | `ticker: string` | ATM options IV % |
| `get_volatility_basket` | `ticker: string` | All metrics + SWOT summary |

## Data Sources

| Metric | Primary | Fallback | Auth |
|--------|---------|----------|------|
| VIX | FRED API | Yahoo Finance | FRED key / None |
| Beta | Yahoo Chart API | - | None |
| Historical Vol | Yahoo Chart API | - | None |
| Implied Vol | Alpha Vantage | - | AV key |

## Usage

### Standalone Test

```bash
source venv/bin/activate
python test_fetchers.py TSLA
```

### Run MCP Server

```bash
source venv/bin/activate
python server.py
```

### Claude Desktop Integration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "volatility-basket": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp-servers/volatility-basket/server.py"]
    }
  }
}
```

### Claude Code Integration

Add to `.mcp.json` in project root:

```json
{
  "servers": {
    "volatility-basket": {
      "command": "mcp-servers/volatility-basket/venv/bin/python",
      "args": ["mcp-servers/volatility-basket/server.py"]
    }
  }
}
```

## API Endpoints Used

```
# FRED (VIX)
GET https://api.stlouisfed.org/fred/series/observations
    ?series_id=VIXCLS&api_key={key}&file_type=json

# Yahoo Finance (price data for Beta, HV)
GET https://query1.finance.yahoo.com/v8/finance/chart/{ticker}
    ?interval=1d&range=1y

# Yahoo Finance (VIX fallback)
GET https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX
```

## Example Output

```json
{
  "ticker": "TSLA",
  "metrics": {
    "vix": {
      "metric": "VIX",
      "value": 14.08,
      "source": "FRED (Federal Reserve)",
      "swot_category": "OPPORTUNITY"
    },
    "beta": {
      "metric": "Beta",
      "value": 2.354,
      "benchmark": "S&P 500",
      "swot_category": "WEAKNESS"
    },
    "historical_volatility": {
      "metric": "Historical Volatility",
      "value": 43.21,
      "unit": "% annualized",
      "swot_category": "WEAKNESS"
    }
  },
  "swot_summary": {
    "strengths": [],
    "weaknesses": ["Beta: 2.354", "HV: 43.21%"],
    "opportunities": ["VIX: 14.08"],
    "threats": []
  }
}
```

## Architecture

```
┌─────────────────────────────────────┐
│         MCP Client (Claude)         │
└──────────────┬──────────────────────┘
               │ stdio (JSON-RPC)
┌──────────────▼──────────────────────┐
│     Volatility Basket MCP Server    │
├─────────────────────────────────────┤
│  get_vix ────────► FRED API         │
│                    ↓ fallback       │
│                    Yahoo Finance    │
│  get_beta ───────► Yahoo Chart API  │
│  get_hist_vol ───► Yahoo Chart API  │
│  get_impl_vol ───► Alpha Vantage    │
└─────────────────────────────────────┘
```

## Files

```
volatility-basket/
├── server.py              # MCP server implementation
├── test_fetchers.py       # Standalone test script
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Package configuration
├── mcp_volatility_basket.md  # Business user guide
└── README.md              # This technical documentation
```

## Rate Limits

| Source | Limit |
|--------|-------|
| Yahoo Finance | ~2000 req/hour |
| FRED | 120 req/minute |
| Alpha Vantage | 25 req/day (free tier) |
