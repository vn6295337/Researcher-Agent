# MCP Data Structures

Output schemas for all MCP basket servers.

---

## fundamentals-basket

```python
"sec_edgar": {
    "revenue": {"value": 123456000, "end_date": "2024-09-30", "data_type": "USD", "fiscal_year": 2024, "form": "10-K"},
    "net_income": {"value": ..., "end_date": ..., ...},
    "gross_profit": {...},
    "operating_income": {...},
    "gross_margin_pct": {...},
    "operating_margin_pct": {...},
    "net_margin_pct": {...},
    "eps_basic": {...},
    "eps_diluted": {...},
    "total_assets": {...},
    "total_liabilities": {...},
    "stockholders_equity": {...},
    "long_term_debt": {...},
    "short_term_debt": {...},
    "total_debt": {...},
    "cash": {...},
    "net_debt": {...},
    "debt_to_equity": {...},
    "operating_cash_flow": {...},
    "capital_expenditure": {...},
    "free_cash_flow": {...},
    "company_info": {
        "name": "Apple Inc.",
        "cik": "0000320193",
        "sic": "3571",
        "sic_description": "Electronic Computers",
        "sector": "Technology",
        "industry": "Consumer Electronics"
    }
},
"yahoo_finance": {
    "market_cap": {"value": 3000000000000, "as_of": "2024-10-31"},
    "enterprise_value": {...},
    "shares_outstanding": {...},
    "float_shares": {...},
    "held_by_insiders_pct": {...},
    "held_by_institutions_pct": {...}
}
```

**Notes:**
- SEC Edgar metrics vary by sector (banks have different fields than tech companies)
- Only non-null values are emitted (sparse representation)

---

## valuation-basket

```python
"yahoo_finance": {
    "current_price": {"value": 175.50, "as_of": "2024-10-31"},
    "trailing_pe": {"value": 28.5, "as_of": "2024-10-31"},
    "forward_pe": {"value": 25.2, "as_of": "2024-10-31"},
    "peg_ratio": {"value": 1.8, "as_of": "2024-10-31"},
    "pb_ratio": {"value": 45.3, "as_of": "2024-10-31"},
    "ps_ratio": {"value": 7.5, "as_of": "2024-10-31"},
    "dividend_yield": {"value": 0.5, "as_of": "2024-10-31"}
},
"alpha_vantage": {
    "trailing_pe": {"value": 28.5, "as_of": "2024-10-31"},
    "forward_pe": {"value": 25.0, "as_of": "2024-10-31"},
    "pb_ratio": {"value": 45.0, "as_of": "2024-10-31"},
    "ps_ratio": {"value": 7.4, "as_of": "2024-10-31"},
    "ev_ebitda": {"value": 22.3, "as_of": "2024-10-31"}
}
```

**Notes:**
- `pb_ratio` = Price-to-Book ratio
- `ps_ratio` = Price-to-Sales ratio (TTM)
- Alpha Vantage provides fallback for all metrics if Yahoo fails

---

## volatility-basket

```python
"fred": {
    "vix": {"value": 18.5, "data_type": "Daily", "as_of": "2024-10-31"},
    "vxn": {"value": 22.1, "data_type": "Daily", "as_of": "2024-10-31"}
},
"yahoo_finance": {
    "beta": {"value": 1.25, "data_type": "1Y", "as_of": "2024-10-31"},
    "historical_volatility": {"value": 0.32, "data_type": "1Y", "as_of": "2024-10-31"},
    "implied_volatility": {"value": 0.28, "as_of": "2024-10-31"}
}
```

---

## macro-basket

```python
"bea": {
    "gdp_growth": {"value": 2.8, "data_type": "Quarterly", "as_of": "2024-09-30"}
},
"bls": {
    "cpi_inflation": {"value": 3.2, "data_type": "Monthly", "as_of": "2024-10-31"},
    "unemployment": {"value": 3.8, "data_type": "Monthly", "as_of": "2024-10-31"}
},
"fred": {
    "interest_rate": {"value": 5.33, "data_type": "Monthly", "as_of": "2024-10-31"}
}
```

**Notes:**
- `cpi_inflation` = Year-over-year CPI inflation rate (%)
- `unemployment` = Unemployment rate (%)
- `interest_rate` = Federal Funds Effective Rate (%)
- FRED provides fallbacks for GDP, CPI, unemployment if BEA/BLS fail

---

## news-basket

```python
"tavily": [
    {"title": "...", "url": "...", "content": "...", "published_date": "2024-10-31"}
],
"nyt": [
    {"title": "...", "url": "...", "content": "...", "published_date": "2024-10-31"}
],
"newsapi": [
    {"title": "...", "url": "...", "content": "...", "published_date": "2024-10-30"}
]
```

**Date field:** `published_date` = actual article publication date (YYYY-MM-DD)

---

## sentiment-basket

```python
"finnhub": [
    {"title": "...", "url": "...", "content": "...", "published_date": "2024-10-31"}
],
"reddit": [
    {"title": "...", "url": "...", "content": "...", "published_date": "2024-10-30"}
]
```

**Date field:** `published_date` = article/post creation date (YYYY-MM-DD)
