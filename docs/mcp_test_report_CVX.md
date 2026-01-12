# MCP E2E Test Report: Chevron Corporation (CVX)

## Summary

| S/N | MCP | Status | Expected | Actual | Duration | Errors | Warnings |
|-----|-----|--------|----------|--------|----------|--------|----------|
| 1 | fundamentals | PASS | 9 | 11 | 12114ms | - | - |
| 2 | valuation | PASS | 11 | 11 | 8105ms | - | - |
| 3 | volatility | PASS | 5 | 5 | 5789ms | - | - |
| 4 | macro | PASS | 4 | 4 | 7236ms | - | - |
| 5 | news | PASS | - | 4 | 6433ms | - | - |
| 6 | sentiment | PASS | - | 55 | 5084ms | - | - |

---

## Quantitative Data

| S/N | Metric | Value | Data Type | As Of | Source | Category |
|-----|--------|-------|-----------|-------|--------|----------|
| 1 | revenue | 193414000000 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 2 | net_income | 17661000000 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 3 | net_margin_pct | 9.13 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 4 | total_assets | 256938000000 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 5 | total_liabilities | 103781000000 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 6 | stockholders_equity | 152318000000 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 7 | oil_gas_revenue | 193414000000 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 8 | depletion | 17282000000 | FY | 2024-12-31 | SEC EDGAR | Fundamentals |
| 9 | total_debt | 41543999488 | Point-in-time | 2025-09-30 | Yahoo Finance | Fundamentals |
| 10 | operating_cash_flow | 31844999168 | TTM | 2025-09-30 | Yahoo Finance | Fundamentals |
| 11 | free_cash_flow | 15743875072 | TTM | 2025-09-30 | Yahoo Finance | Fundamentals |
| 12 | current_price | 162.11 | - | 2026-01-12 | yahoo_finance | Valuation |
| 13 | market_cap | 326622871552.0 | - | 2026-01-12 | yahoo_finance | Valuation |
| 14 | enterprise_value | 365985988608.0 | - | 2026-01-12 | yahoo_finance | Valuation |
| 15 | trailing_pe | 22.76826 | - | 2026-01-12 | yahoo_finance | Valuation |
| 16 | forward_pe | 22.051102 | - | 2026-01-12 | yahoo_finance | Valuation |
| 17 | ps_ratio | 1.73103 | - | 2026-01-12 | yahoo_finance | Valuation |
| 18 | pb_ratio | 1.7193798 | - | 2026-01-12 | yahoo_finance | Valuation |
| 19 | trailing_peg | 3.1673 | - | 2026-01-12 | yahoo_finance | Valuation |
| 20 | forward_peg | - | - | 2026-01-12 | yahoo_finance | Valuation |
| 21 | earnings_growth | -0.266 | - | 2026-01-12 | yahoo_finance | Valuation |
| 22 | revenue_growth | -0.014 | - | 2026-01-12 | yahoo_finance | Valuation |
| 23 | vix | 15.45 | Daily | 2026-01-08 | FRED (Federal Reserve) | Volatility |
| 24 | vxn | 20.15 | Daily | 2026-01-08 | FRED (Federal Reserve) | Volatility |
| 25 | beta | 0.683 | 1Y | 2026-01-09 | Calculated from Yahoo Finance data | Volatility |
| 26 | historical_volatility | 27.6 | 30D | 2026-01-09 | Calculated from Yahoo Finance data | Volatility |
| 27 | implied_volatility | 30.0 | Forward | 2026-01-12 | Market Average (estimated) | Volatility |
| 28 | gdp_growth | 4.3 | Quarterly | 2025Q3 | BEA (Bureau of Economic Analysis) | Macro |
| 29 | interest_rate | 3.72 | Monthly | 2025-12-01 | FRED (Federal Reserve) | Macro |
| 30 | cpi_inflation | 2.74 | Monthly | 2025-November | BLS (Bureau of Labor Statistics) | Macro |
| 31 | unemployment | 4.4 | Monthly | 2025-December | BLS (Bureau of Labor Statistics) | Macro |

---

## Qualitative Data

| S/N | Title | Date | Source | Subreddit | URL | Category |
|-----|-------|------|--------|-----------|-----|----------|
| 1 | Chevron Corporation (CVX) Latest Stock News & Headlines | - | Tavily | - | [Link](https://finance.yahoo.com/quote/CVX/news/) | News |
| 2 | CVX: Chevron Corp - Stock Price, Quote and News | - | Tavily | - | [Link](https://www.cnbc.com/quotes/CVX) | News |
| 3 | CVX Chevron Corporation Stock Price & Overview | - | Tavily | - | [Link](https://seekingalpha.com/symbol/CVX) | News |
| 4 | Chevron - CVX - Stock Price & News | - | Tavily | - | [Link](https://www.fool.com/quote/nyse/cvx/) | News |
| 5 | Trump Pushes Venezuela Oil Investment as Political Risks Loom | 2026-01-12 | Finnhub | - | [Link](https://finnhub.io/api/news?id=4bd9554c63299a6d185eb386ac66113a65a3c2142538b39c2e37d66b773dba22) | Sentiment |
| 6 | Chevron Corporation's (NYSE:CVX) Stock On An Uptrend: Could Fundamentals Be Driv | 2026-01-12 | Finnhub | - | [Link](https://finnhub.io/api/news?id=e73167fa7eed0ebaa552782f612d05724c9bcafa6fd13b2a1ebc2cd040383b13) | Sentiment |
| 7 | Trump's magic number in Venezuela is oil at $50 per barrel | 2026-01-12 | Finnhub | - | [Link](https://finnhub.io/api/news?id=00eea749a137e2ca61c5570e7caf68884968914395d224e7cf5a9b3402ffbf48) | Sentiment |
| 8 | Trump ‘Inclined’ to Keep Exxon Out of Venezuela | 2026-01-12 | Finnhub | - | [Link](https://finnhub.io/api/news?id=e8a561541ca1dd06a87ce7602ca45dde4b4f6c902655bb814d58614f86224f66) | Sentiment |
| 9 | Energy Stocks: Winners And Losers At The Start Of 2026 | 2026-01-11 | Finnhub | - | [Link](https://finnhub.io/api/news?id=fc0a691fdf514129ccf8302385630e7864f71b5a93797d8bd6dfc7a3f95eb1d6) | Sentiment |
| 10 | Energy Secretary Says at Least a Dozen Oil Companies Eager for Venezuela | 2026-01-11 | Finnhub | - | [Link](https://finnhub.io/api/news?id=ac097cc854e23441d94bba402ebd895d68fe4209ee559a614a813bbdc892d913) | Sentiment |
| 11 | Energy Is Still My No. 1 Buy - Even With Venezuela, Politics, And Everything Els | 2026-01-11 | Finnhub | - | [Link](https://finnhub.io/api/news?id=d6fee5c4b9143c17c124b39b2089f158e9763ef335413be7c41afa0f3ecfa69c) | Sentiment |
| 12 | DLN: Diversified Large Value ETF With Risk Screening | 2026-01-11 | Finnhub | - | [Link](https://finnhub.io/api/news?id=f22b9cd12374143fe7f0d9443a755c3efd39b084c1d28926cea65f46dc33a445) | Sentiment |
| 13 | Jim Mellon Says Venezuela's Oil Recovery Is 5+ Years Away, But US Refiners Could | 2026-01-10 | Finnhub | - | [Link](https://finnhub.io/api/news?id=0ca15289a90e3799333ef758956f7336c1d7afb55a6c734b5cb534ff3aab7a4e) | Sentiment |
| 14 | Can Chevron Stock Hit $205 in 2026? | 2026-01-10 | Finnhub | - | [Link](https://finnhub.io/api/news?id=20d3d06abcd6c11df1288a9eec97e52017ecabd73d7d9600b21b19d1b344840f) | Sentiment |
