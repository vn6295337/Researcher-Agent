# MCP Normalized Output Schemas

All 6 MCPs normalized to 3 schema groups for consistent downstream processing.

---

## Group 1: raw_metrics

| MCP | Function | Schema |
|-----|----------|--------|
| volatility-basket | `get_all_sources_volatility` | `{group, ticker, metrics: {name: {value, source, fallback}}}` |
| macro-basket | `get_all_sources_macro` | `{group, ticker, metrics: {name: {value, source, fallback}}}` |

---

## Group 2: source_comparison

| MCP                 | Function                     | Schema                                                    |
| ------------------- | ---------------------------- | --------------------------------------------------------- |
| fundamentals-basket | `get_all_sources_fundamentals` | `{group, ticker, sources: {source_name: {source, data}}}` |
| valuation-basket    | `get_all_sources_valuation`  | `{group, ticker, sources: {source_name: {source, data}}}` |

---

## Group 3: content_analysis

| MCP              | Function                    | Schema                                                              |
| ---------------- | --------------------------- | ------------------------------------------------------------------- |
| news-basket      | `get_all_sources_news`       | `{group, ticker, items: [{title, content, url, datetime, source}]}` |
| sentiment-basket | `get_all_sources_sentiment` | `{group, ticker, items: [{title, content, url, datetime, source}]}` |
