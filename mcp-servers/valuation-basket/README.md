# Valuation Basket MCP Server - Technical Documentation

MCP server for stock valuation multiples from Yahoo Finance.

## Installation

```bash
cd mcp-servers/valuation-basket
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## No API Key Required

Yahoo Finance is free and public. No authentication needed.

## MCP Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `get_pe_ratio` | `ticker` | Price to Earnings (trailing + forward) |
| `get_ps_ratio` | `ticker` | Price to Sales |
| `get_pb_ratio` | `ticker` | Price to Book |
| `get_ev_ebitda` | `ticker` | Enterprise Value to EBITDA |
| `get_peg_ratio` | `ticker` | P/E to Growth ratio |
| `get_valuation_basket` | `ticker` | All metrics + SWOT summary |

## SWOT Interpretation

| Metric | Undervalued | Fair Value | Overvalued |
|--------|-------------|------------|------------|
| P/E | < 15 | 15-25 | > 40 |
| P/S | < 1 | 1-5 | > 10 |
| P/B | < 1 | 1-3 | > 8 |
| EV/EBITDA | < 8 | 8-15 | > 20 |
| PEG | < 1 | 1-1.5 | > 2 |

*Thresholds vary by sector; these are general guidelines.*

## Usage

### Standalone Test

```bash
source venv/bin/activate
python test_fetchers.py AAPL
python test_fetchers.py TSLA pe
python test_fetchers.py NVDA all
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
    "valuation-basket": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp-servers/valuation-basket/server.py"]
    }
  }
}
```

## Example Output

```json
{
  "ticker": "AAPL",
  "metrics": {
    "pe_ratio": {
      "trailing": 28.5,
      "forward": 25.2
    },
    "ps_ratio": 7.8,
    "pb_ratio": 45.3,
    "ev_ebitda": 21.5,
    "peg_ratio": 2.1,
    "enterprise_value": 2850000000000,
    "market_cap": 2900000000000
  },
  "overall_assessment": "Premium valuation on multiple metrics",
  "swot_summary": {
    "opportunities": [],
    "weaknesses": [
      "High P/B (45.3) - Premium to assets",
      "High EV/EBITDA (21.5)",
      "High PEG (2.10) - Overvalued vs growth"
    ]
  }
}
```

## Yahoo Finance API

Uses quoteSummary endpoint:
```
GET https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryDetail,defaultKeyStatistics,financialData
```

**Rate Limits:** Unofficial API, be respectful with request frequency.

## Files

```
valuation-basket/
├── server.py           # MCP server implementation
├── test_fetchers.py    # Standalone test script
├── requirements.txt    # Python dependencies
└── README.md           # This documentation
```
