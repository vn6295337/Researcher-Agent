## Overview

Standardized output schema for financial data across ALL industries (banks, consumer goods, tech, etc.)

---

## Quantitative Metrics

### 1. Fundamentals (9 metrics)

| Source | Metric | Description | Universal? |
|--------|--------|-------------|:----------:|
| **SEC EDGAR** | `revenue` | Total revenue (FY) | ✓ |
| **SEC EDGAR** | `net_income` | Net income (FY) | ✓ |
| **SEC EDGAR** | `net_margin_pct` | Net Income / Revenue % | ✓ |
| **SEC EDGAR** | `total_assets` | Total assets | ✓ |
| **SEC EDGAR** | `total_liabilities` | Total liabilities | ✓ |
| **SEC EDGAR** | `stockholders_equity` | Shareholders' equity | ✓ |
| **Yahoo Finance** | `operating_margin_pct` | Operating margin % (TTM) | Supplementary |
| **Yahoo Finance** | `total_debt` | Total debt (TTM) | Supplementary |
| **Yahoo Finance** | `operating_cash_flow` | Operating cash flow (TTM) | Supplementary |
| **Yahoo Finance** | `free_cash_flow` | Free cash flow (TTM) | Supplementary |

**Sources:**
```
┌────┬───────────────┬───────────┬───────────────────────────────────────┐
│ #  │ Source        │ Data Type │ Notes                                 │
├────┼───────────────┼───────────┼───────────────────────────────────────┤
│ 1  │ SEC EDGAR     │ FY (10-K) │ Primary - official filings            │
│ 2  │ Yahoo Finance │ TTM       │ Supplementary + Fallback if SEC fails │
└────┴───────────────┴───────────┴───────────────────────────────────────┘
```

---

### 2. Valuation (11 metrics)

| Source | Metric | Description |
|--------|--------|-------------|
| **Yahoo Finance** | `current_price` | Current stock price |
| **Yahoo Finance** | `market_cap` | Market capitalization |
| **Yahoo Finance** | `enterprise_value` | Enterprise value |
| **Yahoo Finance** | `trailing_pe` | Trailing P/E ratio |
| **Yahoo Finance** | `forward_pe` | Forward P/E ratio |
| **Yahoo Finance** | `ps_ratio` | Price-to-Sales ratio |
| **Yahoo Finance** | `pb_ratio` | Price-to-Book ratio |
| **Yahoo Finance** | `trailing_peg` | Trailing PEG ratio |
| **Yahoo Finance** | `forward_peg` | Forward PEG ratio |
| **Yahoo Finance** | `earnings_growth` | Earnings growth rate |
| **Yahoo Finance** | `revenue_growth` | Revenue growth rate |

**Sources:**
```
┌────┬───────────────┬─────────────────────────────────┐
│ #  │ Source        │ Notes                           │
├────┼───────────────┼─────────────────────────────────┤
│ 1  │ Yahoo Finance │ Primary - real-time quotes      │
│ 2  │ Alpha Vantage │ Fallback if Yahoo Finance fails │
└────┴───────────────┴─────────────────────────────────┘
```
**Excluded:** `ev_ebitda` (banks don't report EBITDA)

---

### 3. Volatility (5 metrics)

| Source | Metric | Description |
|--------|--------|-------------|
| **FRED** | `vix` | CBOE Volatility Index (S&P 500) |
| **FRED** | `vxn` | CBOE NASDAQ Volatility Index |
| **Calculated** | `beta` | 1-year beta vs S&P 500 |
| **Calculated** | `historical_volatility` | 30-day historical volatility |
| **Estimated** | `implied_volatility` | Forward implied volatility |

**Sources:**
```
┌─────────────────────┬─────────────────┬───────────────────────────┐
│ Metric              │ Primary         │ Fallback                  │
├─────────────────────┼─────────────────┼───────────────────────────┤
│ vix, vxn            │ FRED            │ -                         │
│ beta                │ Yahoo Finance   │ Alpha Vantage             │
│ historical_vol      │ Yahoo Finance   │ Alpha Vantage             │
│ implied_vol         │ Options Chain   │ Market average (30%)      │
└─────────────────────┴─────────────────┴───────────────────────────┘
```

---

### 4. Macro (4 metrics)

| Source | Metric | Description |
|--------|--------|-------------|
| **BEA** | `gdp_growth` | GDP growth rate (quarterly) |
| **FRED** | `interest_rate` | Federal funds rate |
| **BLS** | `cpi_inflation` | CPI inflation rate |
| **BLS** | `unemployment` | Unemployment rate |

**Sources:**
```
┌─────────────────────┬─────────────────┬───────────────────────────┐
│ Metric              │ Primary         │ Fallback                  │
├─────────────────────┼─────────────────┼───────────────────────────┤
│ gdp_growth          │ BEA             │ FRED                      │
│ interest_rate       │ FRED            │ -                         │
│ cpi_inflation       │ BLS             │ FRED                      │
│ unemployment        │ BLS             │ FRED                      │
└─────────────────────┴─────────────────┴───────────────────────────┘
```

---

## Qualitative Data

### 5. News (variable count)

| Field | Description |
|-------|-------------|
| `title` | Article headline |
| `date` | Publication date |
| `source` | News source (Tavily, NYT, NewsAPI) |
| `url` | Link to article |

**Sources (parallel, equally weighted):**
```
┌─────────┬─────────────────────────────┐
│ Source  │ Notes                       │
├─────────┼─────────────────────────────┤
│ Tavily  │ AI-powered search           │
│ NewsAPI │ Financial news aggregator   │
│ NYT     │ New York Times API          │
└─────────┴─────────────────────────────┘
```

---

### 6. Sentiment (variable count)

| Field | Description |
|-------|-------------|
| `title` | Post/article headline |
| `date` | Publication date |
| `source` | Source (Finnhub, Reddit) |
| `subreddit` | Reddit subreddit (if applicable) |
| `url` | Link to source |

**Sources (parallel, equally weighted):**
```
┌─────────┬───────────────────────────────────┐
│ Source  │ Notes                             │
├─────────┼───────────────────────────────────┤
│ Finnhub │ Company news & sentiment          │
│ Reddit  │ r/wallstreetbets, r/stocks        │
└─────────┴───────────────────────────────────┘
```

---

## Expected Counts

| MCP | Expected | Rationale |
|-----|:--------:|-----------|
| fundamentals | 9 | SEC (6) + Yahoo (4 supplementary, ~1 null) |
| valuation | 11 | Yahoo Finance only, universal metrics |
| volatility | 5 | All universal |
| macro | 4 | All universal |
| news | - | Variable (depends on news cycle) |
| sentiment | - | Variable (depends on activity) |

---

## Files Implementing This Schema

| File                                                       | Environment | Purpose                             |
| ---------------------------------------------------------- | ----------- | ----------------------------------- |
| `mcp-servers/fundamentals-basket/server_legacy.py`         | Test        | Direct import for E2E tests         |
| `mcp-servers/fundamentals-basket/services/orchestrator.py` | Production  | Via http_server.py → server.py      |
| `mcp-servers/valuation-basket/server.py`                   | Both        | get_all_sources_valuation()         |
| `mcp-servers/volatility-basket/server.py`                  | Both        | get_all_sources_volatility()        |
| `mcp-servers/macro-basket/server.py`                       | Both        | get_all_sources_macro()             |
| `tests/test_mcp_e2e.py`                                    | Test        | E2E validation with expected counts |

---

## Output Format

### Aggregated Response (from `fetch_all_research_data`)

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "sources_available": ["fundamentals", "valuation", "volatility", "macro", "news", "sentiment"],
  "sources_failed": [],
  "metrics": {
    "fundamentals": { ... },
    "valuation": { ... },
    "volatility": { ... },
    "macro": { ... },
    "news": { ... },
    "sentiment": { ... }
  },
  "multi_source": {
    "fundamentals_all": { ... },
    "valuation_all": { ... },
    "macro_all": { ... },
    "volatility_all": { ... }
  },
  "conflict_resolution": { ... },
  "aggregated_swot": { ... },
  "completeness": {
    "completeness_pct": 85.0,
    "metrics_found": 17,
    "metrics_total": 20,
    "missing": { ... }
  },
  "generated_at": "2025-01-11T21:00:00"
}
```

---

### Fundamentals Output

```json
{
  "sec_edgar": {
    "source": "SEC EDGAR XBRL",
    "data": {
      "revenue": {"value": 383285000000, "end_date": "2024-09-28", "fiscal_year": 2024, "form": "10-K"},
      "net_income": {"value": 93736000000, "end_date": "2024-09-28", "fiscal_year": 2024, "form": "10-K"},
      "net_margin_pct": {"value": 24.45, "end_date": "2024-09-28", "fiscal_year": 2024, "form": "10-K"},
      "total_assets": {"value": 364980000000},
      "total_liabilities": {"value": 308030000000},
      "stockholders_equity": {"value": 56950000000}
    }
  },
  "yahoo_finance": {
    "source": "Yahoo Finance",
    "data": {
      "operating_margin_pct": 30.74,
      "total_debt": 106629000000,
      "operating_cash_flow": 118254000000,
      "free_cash_flow": 111443000000
    }
  }
}
```

---

### Valuation Output

```json
{
  "yahoo_finance": {
    "source": "Yahoo Finance",
    "data": {
      "current_price": 229.87,
      "market_cap": 3480000000000,
      "enterprise_value": 3580000000000,
      "trailing_pe": 37.12,
      "forward_pe": 31.45,
      "ps_ratio": 9.08,
      "pb_ratio": 61.11,
      "trailing_peg": 2.89,
      "forward_peg": 2.15,
      "earnings_growth": 0.1047,
      "revenue_growth": 0.0204
    }
  },
  "alpha_vantage": {
    "source": "Alpha Vantage",
    "data": { ... }
  }
}
```

---

### Volatility Output

```json
{
  "yahoo_finance": {
    "source": "Yahoo Finance",
    "data": {
      "beta": {"value": 1.24},
      "historical_volatility": {"value": 22.5},
      "implied_volatility": {"value": null}
    }
  },
  "market_volatility_context": {
    "vix": {"value": 15.45, "date": "2025-01-10"},
    "vxn": {"value": 18.32, "date": "2025-01-10"}
  }
}
```

---

### Macro Output

```json
{
  "bea_bls": {
    "source": "BEA/BLS",
    "data": {
      "gdp_growth": {"value": 4.30, "date": "2024-09-01"},
      "cpi_inflation": {"value": 2.74, "date": "2024-12-01"},
      "unemployment": {"value": 4.40, "date": "2024-12-01"}
    }
  },
  "fred": {
    "source": "FRED",
    "data": {
      "interest_rate": {"value": 3.72, "date": "2025-01-09"}
    }
  }
}
```

---

### News Output

```json
{
  "group": "content_analysis",
  "ticker": "AAPL",
  "items": [
    {
      "title": "Apple Reports Record Q4 Earnings",
      "content": "Apple Inc. reported...",
      "url": "https://...",
      "datetime": "2025-01-10",
      "source": "Tavily"
    }
  ],
  "item_count": 10,
  "sources_used": ["Tavily", "NYT", "NewsAPI"],
  "source": "news-basket",
  "as_of": "2025-01-11"
}
```

---

### Sentiment Output

```json
{
  "group": "content_analysis",
  "ticker": "AAPL",
  "items": [
    {
      "title": "AAPL to the moon!",
      "content": "Just loaded up on more shares...",
      "url": "https://reddit.com/r/wallstreetbets/...",
      "datetime": "2025-01-10",
      "source": "Reddit",
      "subreddit": "r/wallstreetbets"
    },
    {
      "title": "Apple Announces New Product Line",
      "content": "Apple Inc. unveiled...",
      "url": "https://finnhub.io/...",
      "datetime": "2025-01-09",
      "source": "Finnhub",
      "subreddit": null
    }
  ],
  "item_count": 15,
  "sources_used": ["Finnhub", "Reddit"],
  "source": "sentiment-basket",
  "as_of": "2025-01-11"
}
```

---

### Streamed Metrics (partial_metrics)

During task execution, metrics are streamed as:

```json
{
  "source": "fundamentals",
  "metric": "revenue",
  "value": 383285000000,
  "timestamp": "2025-01-11T21:00:01",
  "end_date": "2024-09-28",
  "fiscal_year": 2024,
  "form": "10-K"
}
```

| Source | Metrics Streamed |
|--------|------------------|
| fundamentals | `revenue`, `net_margin` |
| valuation | `P/E`, `P/B`, `P/S`, `EV/EBITDA` |
| volatility | `VIX`, `beta`, `hist_vol` |
| macro | `GDP_growth`, `interest_rate`, `inflation`, `unemployment` |
| news | `items_found` (count) |
| sentiment | `items_found` (count) |
