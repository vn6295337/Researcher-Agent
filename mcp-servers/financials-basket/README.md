# Financials Basket MCP Server - Technical Documentation

MCP server for fetching fundamental financial data from SEC EDGAR XBRL.

## Installation

```bash
cd mcp-servers/financials-basket
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## No API Key Required

SEC EDGAR is free and public. Rate limit: 10 requests/second.

## MCP Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `get_company_info` | `ticker` | Company name, CIK, industry (SIC) |
| `get_financials` | `ticker` | Revenue, income, margins, growth |
| `get_debt_metrics` | `ticker` | Debt levels, debt-to-equity |
| `get_cash_flow` | `ticker` | Operating CF, CapEx, FCF, R&D |
| `get_material_events` | `ticker`, `limit` | Recent 8-K filings with risk flags |
| `get_ownership_filings` | `ticker`, `limit` | 13D/13G (5%+ owners), Form 4 (insiders) |
| `get_going_concern` | `ticker` | 10-K text search for going concern warnings |
| `get_sec_fundamentals` | `ticker` | All metrics + SWOT summary |

## API Endpoints Used

```
# Company tickers (CIK lookup)
GET https://www.sec.gov/files/company_tickers.json

# Company submissions
GET https://data.sec.gov/submissions/CIK{cik}.json

# Company facts (XBRL)
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
```

## XBRL Concepts Extracted

| Category | XBRL Concept |
|----------|--------------|
| Revenue | `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax` |
| Net Income | `NetIncomeLoss` |
| Gross Profit | `GrossProfit` |
| Operating Income | `OperatingIncomeLoss` |
| Assets | `Assets` |
| Liabilities | `Liabilities` |
| Equity | `StockholdersEquity` |
| Long-term Debt | `LongTermDebt`, `LongTermDebtNoncurrent` |
| Short-term Debt | `ShortTermBorrowings`, `DebtCurrent` |
| Cash | `CashAndCashEquivalentsAtCarryingValue` |
| Operating CF | `NetCashProvidedByUsedInOperatingActivities` |
| CapEx | `PaymentsToAcquirePropertyPlantAndEquipment` |
| R&D | `ResearchAndDevelopmentExpense` |

## Going Concern Keywords

The `get_going_concern` tool searches the latest 10-K for these phrases:

| Keyword | Risk Signal |
|---------|-------------|
| "going concern" | Auditor/management concern |
| "substantial doubt" | High risk language |
| "ability to continue" | Viability question |
| "material uncertainty" | Significant risk |
| "liquidity concerns" | Cash flow issues |

**Risk Levels:**
- `none`: No keywords found
- `low`: Few mentions (often boilerplate)
- `medium`: 5+ mentions
- `high`: "substantial doubt" present

## Ownership Filings

| Form | Trigger | What It Means |
|------|---------|---------------|
| SC 13D | >5% ownership + intent to influence | Activist investor, potential changes |
| SC 13G | >5% ownership (passive) | Large institutional position |
| Form 3 | Initial insider statement | New officer/director/10%+ owner |
| Form 4 | Insider transaction | Buy/sell by officer/director |
| Form 5 | Annual summary | Year-end insider ownership |

## 8-K Material Event Codes

High-priority events flagged for SWOT analysis:

| Code | Event | SWOT Category |
|------|-------|---------------|
| 1.03 | Bankruptcy or Receivership | Threat |
| 2.04 | Triggering Events (Debt Acceleration) | Threat |
| 2.06 | Material Impairments | Weakness |
| 3.01 | Delisting Notice | Threat |
| 4.02 | Non-Reliance on Prior Financials | Threat |
| 5.01 | Change in Control | Weakness |
| 5.02 | Executive/Director Departure | Weakness |

## Usage

### Standalone Test

```bash
source venv/bin/activate
python test_fetchers.py AAPL
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
    "financials-basket": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp-servers/financials-basket/server.py"]
    }
  }
}
```

## Example Output

```json
{
  "ticker": "AAPL",
  "financials": {
    "revenue": {"value": 383285000000, "fiscal_year": 2023},
    "net_income": {"value": 96995000000},
    "revenue_growth_3yr": 8.5,
    "net_margin_pct": 25.3,
    "operating_margin_pct": 29.8
  },
  "debt": {
    "long_term_debt": {"value": 95281000000},
    "debt_to_equity": 1.81
  },
  "cash_flow": {
    "operating_cash_flow": {"value": 110543000000},
    "free_cash_flow": {"value": 99584000000}
  },
  "swot_summary": {
    "strengths": [
      "Positive revenue growth: 8.5% CAGR (3yr)",
      "High profitability: 25.3% net margin",
      "Positive free cash flow: $99.6B"
    ],
    "weaknesses": [
      "Elevated debt: 1.81x debt-to-equity"
    ]
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
│     Financials Basket MCP Server    │
├─────────────────────────────────────┤
│  ticker_to_cik ──► company_tickers  │
│  get_company_info ► submissions API │
│  get_financials ──► XBRL facts API  │
│  get_debt_metrics ► XBRL facts API  │
│  get_cash_flow ───► XBRL facts API  │
└─────────────────────────────────────┘
```

## Files

```
financials-basket/
├── server.py           # MCP server implementation
├── test_fetchers.py    # Standalone test script
├── requirements.txt    # Python dependencies
├── mcp_sec_edgar.md    # Business user guide
└── README.md           # This technical documentation
```

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| SEC EDGAR | 10 req/sec |

**Important:** SEC requires a User-Agent header with contact info.
