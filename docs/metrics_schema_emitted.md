## MCP Output Schema - Emitted Format

JSON/dict structure returned by each `get_all_sources_*()` function.

---

## 1. `get_all_sources_fundamentals(ticker)`

```
{
    "ticker": str,
    "sec_edgar": {
        "source": str,
        "as_of": str,
        "data": {
            "revenue": {"value": float, "end_date": str, "fiscal_year": int, "form": str} | null,
            "net_income": {"value": float, "end_date": str, "fiscal_year": int, "form": str} | null,
            "net_margin_pct": {"value": float, "end_date": str, "fiscal_year": int, "form": str} | null,
            "total_assets": {"value": float, "end_date": str, "fiscal_year": int, "form": str} | null,
            "total_liabilities": {"value": float, "end_date": str, "fiscal_year": int, "form": str} | null,
            "stockholders_equity": {"value": float, "end_date": str, "fiscal_year": int, "form": str} | null
        }
    },
    "yahoo_finance": {
        "source": str,
        "as_of": str,
        "data": {
            "operating_margin_pct": {"value": float} | null,
            "total_debt": {"value": float} | null,
            "operating_cash_flow": {"value": float} | null,
            "free_cash_flow": {"value": float} | null
        }
    },
    "generated_at": str
}
```

**Notes:**
- SEC EDGAR: 6 universal metrics (FY data with temporal fields)
- Yahoo Finance: 4 supplementary metrics (TTM data)
- If SEC fails, Yahoo provides fallback core metrics (revenue, net_income, net_margin_pct, total_assets)

---

## 2. `get_all_sources_valuation(ticker)`

```
{
    "group": "source_comparison",
    "ticker": str,
    "sources": {
        "yahoo_finance": {
            "source": str,
            "regular_market_time": str,
            "data": {
                "current_price": float | null,
                "market_cap": float | null,
                "enterprise_value": float | null,
                "trailing_pe": float | null,
                "forward_pe": float | null,
                "ps_ratio": float | null,
                "pb_ratio": float | null,
                "trailing_peg": float | null,
                "forward_peg": float | null,
                "earnings_growth": float | null,
                "revenue_growth": float | null
            }
        }
    },
    "source": str,
    "as_of": str
}
```

**Notes:**
- 11 universal metrics (excludes ev_ebitda - banks don't report EBITDA)
- If Yahoo fails, `alpha_vantage` key replaces `yahoo_finance`

---

## 3. `get_all_sources_volatility(ticker)`

```
{
    "group": "raw_metrics",
    "ticker": str,
    "metrics": {
        "vix": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        },
        "vxn": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        },
        "beta": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        },
        "historical_volatility": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        },
        "implied_volatility": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        }
    },
    "source": str,
    "as_of": str
}
```

**Notes:**
- `data_type` values: "Daily" (VIX/VXN), "1Y" (beta), "30D" (historical_vol), "Forward" (implied_vol)

---

## 4. `get_all_sources_macro()`

```
{
    "group": "raw_metrics",
    "ticker": "MACRO",
    "metrics": {
        "gdp_growth": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        },
        "interest_rate": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        },
        "cpi_inflation": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        },
        "unemployment": {
            "value": float | null,
            "data_type": str,
            "as_of": str,
            "source": str,
            "fallback": bool
        }
    },
    "source": str,
    "as_of": str
}
```

**Notes:**
- `data_type` values: "Quarterly" (GDP), "Monthly" (interest_rate, cpi, unemployment)
- `as_of` format varies: "2025Q3" (GDP), "2025-01" (monthly)

---

## 5. `get_all_sources_news(ticker, company_name)`

```
{
    "group": "content_analysis",
    "ticker": str,
    "query": str,
    "items": [
        {
            "title": str | null,
            "content": str | null,
            "url": str | null,
            "datetime": str | null,
            "source": str
        }
    ],
    "item_count": int,
    "sources_used": [str],
    "source": str,
    "as_of": str
}
```

**Notes:**
- `sources_used`: ["Tavily", "NYT", "NewsAPI"]
- `datetime`: YYYY-MM-DD format

---

## 6. `get_all_sources_sentiment(ticker, company_name)`

```
{
    "group": "content_analysis",
    "ticker": str,
    "items": [
        {
            "title": str | null,
            "content": str | null,
            "url": str | null,
            "datetime": str | null,
            "source": str,
            "subreddit": str | null
        }
    ],
    "item_count": int,
    "sources_used": [str],
    "source": str,
    "as_of": str
}
```

**Notes:**
- `sources_used`: ["Finnhub", "Reddit"]
- `subreddit`: Only populated for Reddit items (e.g., "r/wallstreetbets")
- `datetime`: YYYY-MM-DD format
