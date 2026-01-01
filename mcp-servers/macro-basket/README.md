# Macro Basket MCP Server - Technical Documentation

MCP server for macroeconomic indicators from FRED (Federal Reserve Economic Data).

## Installation

```bash
cd mcp-servers/macro-basket
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## API Key Required

Get free API key at: https://fred.stlouisfed.org/docs/api/api_key.html

Add to `~/.env`:
```
FRED_API_KEY=your_api_key_here
```

**Free tier:** Unlimited requests (10 req/sec rate limit)

## MCP Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `get_gdp` | None | Real GDP growth rate (quarterly, annualized) |
| `get_interest_rates` | None | Federal Funds Effective Rate |
| `get_cpi` | None | Consumer Price Index, YoY inflation rate |
| `get_unemployment` | None | Unemployment rate |
| `get_macro_basket` | None | All metrics + SWOT summary |

## FRED Series Used

| Metric | Series ID | Frequency |
|--------|-----------|-----------|
| GDP Growth | A191RL1Q225SBEA | Quarterly |
| Interest Rate | FEDFUNDS | Monthly |
| CPI | CPIAUCSL | Monthly |
| Unemployment | UNRATE | Monthly |

## SWOT Interpretation

| Metric | Favorable | Unfavorable |
|--------|-----------|-------------|
| GDP Growth | > 3% (strong growth) | < 0% (contraction) |
| Interest Rate | < 3% (low borrowing costs) | > 5% (tight policy) |
| CPI/Inflation | 1-2% (stable prices) | > 4% (high inflation) |
| Unemployment | < 4% (tight labor market) | > 6% (weak labor market) |

## Usage

### Standalone Test

```bash
source venv/bin/activate
python test_fetchers.py
python test_fetchers.py gdp
python test_fetchers.py all
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
    "macro-basket": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp-servers/macro-basket/server.py"]
    }
  }
}
```

## Example Output

```json
{
  "basket": "Macro Indicators",
  "metrics": {
    "gdp_growth": {
      "metric": "GDP Growth",
      "value": 2.8,
      "unit": "% change (quarterly, annualized)",
      "interpretation": "Moderate growth - Stable economic conditions",
      "swot_category": "NEUTRAL"
    },
    "interest_rate": {
      "metric": "Federal Funds Rate",
      "value": 5.33,
      "unit": "%",
      "trend": "stable",
      "interpretation": "High interest rates (stable) - Tight monetary policy",
      "swot_category": "THREAT"
    },
    "cpi_inflation": {
      "metric": "CPI / Inflation",
      "value": 3.2,
      "unit": "% YoY",
      "interpretation": "Moderate inflation - Near Fed target (2%)",
      "swot_category": "NEUTRAL"
    },
    "unemployment": {
      "metric": "Unemployment Rate",
      "value": 4.1,
      "unit": "%",
      "trend": "stable",
      "interpretation": "Normal unemployment (stable) - Healthy labor market",
      "swot_category": "NEUTRAL"
    }
  },
  "overall_assessment": "Mixed macroeconomic conditions with headwinds",
  "swot_summary": {
    "opportunities": [],
    "threats": ["Federal Funds Rate: 5.33% - High interest rates"]
  }
}
```

## Files

```
macro-basket/
├── server.py           # MCP server implementation
├── test_fetchers.py    # Standalone test script
├── requirements.txt    # Python dependencies
└── README.md           # This documentation
```
