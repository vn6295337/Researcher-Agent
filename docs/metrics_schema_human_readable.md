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

## Output Format (Example: Apple Inc.)

### Summary

| S/N | MCP | Status | Expected | Actual | Source |
|-----|-----|--------|----------|--------|--------|
| 1 | fundamentals | PASS | 9 | 9 | SEC EDGAR + Yahoo Finance |
| 2 | valuation | PASS | 11 | 11 | Yahoo Finance |
| 3 | volatility | PASS | 5 | 5 | FRED + Yahoo Finance |
| 4 | macro | PASS | 4 | 4 | BEA + BLS + FRED |
| 5 | news | PASS | - | 10 | Tavily + NYT + NewsAPI |
| 6 | sentiment | PASS | - | 15 | Finnhub + Reddit |

---

### Quantitative Data

| S/N | Metric | Value | Data Type | As Of | Source | Category |
|-----|--------|-------|-----------|-------|--------|----------|
| 1 | revenue | 383,285,000,000 | FY | 2024-09-28 | SEC EDGAR | Fundamentals |
| 2 | net_income | 93,736,000,000 | FY | 2024-09-28 | SEC EDGAR | Fundamentals |
| 3 | net_margin_pct | 24.45 | FY | 2024-09-28 | SEC EDGAR | Fundamentals |
| 4 | total_assets | 364,980,000,000 | FY | 2024-09-28 | SEC EDGAR | Fundamentals |
| 5 | total_liabilities | 308,030,000,000 | FY | 2024-09-28 | SEC EDGAR | Fundamentals |
| 6 | stockholders_equity | 56,950,000,000 | FY | 2024-09-28 | SEC EDGAR | Fundamentals |
| 7 | operating_margin_pct | 30.74 | TTM | 2025-01-11 | Yahoo Finance | Fundamentals |
| 8 | total_debt | 106,629,000,000 | TTM | 2025-01-11 | Yahoo Finance | Fundamentals |
| 9 | free_cash_flow | 111,443,000,000 | TTM | 2025-01-11 | Yahoo Finance | Fundamentals |
| 10 | current_price | 229.87 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 11 | market_cap | 3,480,000,000,000 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 12 | enterprise_value | 3,580,000,000,000 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 13 | trailing_pe | 37.12 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 14 | forward_pe | 31.45 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 15 | ps_ratio | 9.08 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 16 | pb_ratio | 61.11 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 17 | trailing_peg | 2.89 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 18 | forward_peg | 2.15 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 19 | earnings_growth | 0.1047 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 20 | revenue_growth | 0.0204 | - | 2025-01-11 | Yahoo Finance | Valuation |
| 21 | vix | 15.45 | Daily | 2025-01-10 | FRED | Volatility |
| 22 | vxn | 18.32 | Daily | 2025-01-10 | FRED | Volatility |
| 23 | beta | 1.24 | 1Y | 2025-01-11 | Yahoo Finance | Volatility |
| 24 | historical_volatility | 22.50 | 30D | 2025-01-11 | Yahoo Finance | Volatility |
| 25 | implied_volatility | 30.00 | Forward | 2025-01-11 | Market Average | Volatility |
| 26 | gdp_growth | 4.30 | Quarterly | 2024-Q3 | BEA | Macro |
| 27 | interest_rate | 3.72 | Monthly | 2025-01-09 | FRED | Macro |
| 28 | cpi_inflation | 2.74 | Monthly | 2024-12-01 | BLS | Macro |
| 29 | unemployment | 4.40 | Monthly | 2024-12-01 | BLS | Macro |

---

### Qualitative Data

| S/N | Title | Date | Source | Subreddit | URL | Category |
|-----|-------|------|--------|-----------|-----|----------|
| 1 | Apple Reports Record Q4 Earnings | 2025-01-10 | Tavily | - | [Link](https://...) | News |
| 2 | Apple Stock Rises on Strong iPhone Sales | 2025-01-09 | NYT | - | [Link](https://...) | News |
| 3 | AAPL Analysis: Buy or Hold? | 2025-01-08 | NewsAPI | - | [Link](https://...) | News |
| 4 | Apple Announces New Product Line | 2025-01-10 | Finnhub | - | [Link](https://...) | Sentiment |
| 5 | Apple's AI Strategy Impresses Analysts | 2025-01-09 | Finnhub | - | [Link](https://...) | Sentiment |
| 6 | AAPL to the moon! | 2025-01-10 | Reddit | r/wallstreetbets | [Link](https://...) | Sentiment |
| 7 | Why I'm bullish on Apple for 2025 | 2025-01-09 | Reddit | r/stocks | [Link](https://...) | Sentiment |

---

### Streamed Metrics (Real-time)

During task execution, these metrics are streamed to the frontend:

| S/N | Source | Metric | Example Value | Temporal Info |
|-----|--------|--------|---------------|---------------|
| 1 | fundamentals | revenue | 383,285,000,000 | FY 2024 |
| 2 | fundamentals | net_margin | 24.45 | FY 2024 |
| 3 | valuation | P/E | 37.12 | - |
| 4 | valuation | P/B | 61.11 | - |
| 5 | valuation | P/S | 9.08 | - |
| 6 | volatility | VIX | 15.45 | - |
| 7 | volatility | beta | 1.24 | - |
| 8 | volatility | hist_vol | 22.50 | - |
| 9 | macro | GDP_growth | 4.30 | - |
| 10 | macro | interest_rate | 3.72 | - |
| 11 | macro | inflation | 2.74 | - |
| 12 | macro | unemployment | 4.40 | - |
| 13 | news | items_found | 10 | - |
| 14 | sentiment | items_found | 15 | - |
