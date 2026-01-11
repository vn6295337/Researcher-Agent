## Problem

| MCP | Emits | Analyzer Expects |
|-----|-------|------------------|
| volatility | `{"metrics": {"vix": ...}}` | `{"yahoo_finance": {"data": {...}}}` |
| macro | `{"metrics": {"gdp_growth": ...}}` | `{"bea_bls": {"data": {...}}}` |

## Solution

| Step | Component | Action |
|:----:|-----------|--------|
| 1 | MCP servers | Emit raw schemas |
| 2 | **mcp_client.py** | `_normalize_*()` adapters |
| 3 | A2A | Pass normalized data |
| 4 | Analyzer | Consume consistent schema |

## Why Source-Centric (not MCP-Centric)

| Human View (6 MCPs) | | Processing View (by source) | |
|---------------------|---|-----------------------------|----|
| fundamentals | → | SEC EDGAR | primary |
| valuation | → | Yahoo Finance | fallback |
| volatility | → | Alpha Vantage | fallback |
| macro | → | FRED / BEA / BLS | |
| news | → | Tavily / NYT / NewsAPI | |
| sentiment | → | Finnhub / Reddit | |

**MCPs** = fetch boundaries · **Sources** = conflict resolution

### Example: Fundamentals MCP

| Human View | | Processing View | |
|------------|---|-----------------|---|
| **fundamentals** | | **SEC EDGAR** | primary |
| - revenue | → | - revenue | |
| - net_income | | - net_income | |
| - margins | | | |
| | | **Yahoo Finance** | fallback |
| | | - operating_cf | |

## Target Schema (Source-Keyed)

```python
{
    "sources": {
        "sec_edgar":     {"revenue": {...}, "net_income": {...}},
        "yahoo_finance": {"beta": {...}, "trailing_pe": {...}},
        "fred":          {"vix": {...}, "interest_rate": {...}},
        "bea_bls":       {"gdp_growth": {...}, "unemployment": {...}},
        "tavily":        {"items": [...]},
        "finnhub":       {"items": [...]},
    }
}
```
