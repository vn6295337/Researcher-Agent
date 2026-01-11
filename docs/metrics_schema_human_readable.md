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
