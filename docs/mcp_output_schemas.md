# MCP Server Output Schemas

## fundamentals-basket
sec_edgar: { data: { revenue, net_income, net_margin_pct, total_assets, total_liabilities, stockholders_equity } }
yahoo_finance: { data: { operating_margin_pct, total_debt, operating_cash_flow, free_cash_flow } }

## valuation-basket
yahoo_finance: { data: { current_price, market_cap, pe_ratio, forward_pe, ps_ratio, pb_ratio, ev_ebitda, peg_ratio } }

## volatility-basket
fred: { data: { vix, vxn } }
yahoo_finance: { data: { beta, historical_volatility, implied_volatility } }

## macro-basket
bea: { data: { gdp_growth } }
bls: { data: { cpi_inflation, unemployment } }
fred: { data: { interest_rate } }

## news-basket
tavily: { data: { articles[]: { title, url, content, score, published_date } } }
nyt: { data: { articles[]: { headline, url, snippet, pub_date } } }
newsapi: { data: { articles[]: { title, url, description, publishedAt, source } } }

## sentiment-basket
finnhub: { data: { articles[]: { headline, summary, url, source, datetime } } }
reddit: { data: { posts[]: { title, selftext, permalink, ups, created_utc } } }
