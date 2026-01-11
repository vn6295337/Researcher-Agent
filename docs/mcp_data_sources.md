

### fundamentals-basket (29 metrics)

| S/N | metric                    | temporal info | primary       | secondary     |
| --- | ------------------------- | ------------- | ------------- | ------------- |
|     | **Income Statement**      |               |               |               |
| 1   | Revenue                   | FY            | SEC EDGAR     | Yahoo Finance |
| 2   | Gross Profit              | FY            | SEC EDGAR     | Yahoo Finance |
| 3   | Operating Income          | FY            | SEC EDGAR     | Yahoo Finance |
| 4   | Net Income                | FY            | SEC EDGAR     | Yahoo Finance |
|     | **Balance Sheet**         |               |               |               |
| 5   | Total Assets              | Q             | SEC EDGAR     | Yahoo Finance |
| 6   | Total Liabilities         | Q             | SEC EDGAR     | Yahoo Finance |
| 7   | Stockholders Equity       | Q             | SEC EDGAR     | Yahoo Finance |
| 8   | Cash                      | Q             | SEC EDGAR     | Yahoo Finance |
| 9   | Long Term Debt            | Q             | SEC EDGAR     | Yahoo Finance |
| 10  | Total Debt                | Q             | SEC EDGAR     | Yahoo Finance |
|     | **Cash Flow**             |               |               |               |
| 11  | Operating Cash Flow       | FY            | SEC EDGAR     | Yahoo Finance |
| 12  | Capital Expenditure       | FY            | SEC EDGAR     | Yahoo Finance |
| 13  | Free Cash Flow            | FY            | SEC EDGAR     | Yahoo Finance |
| 14  | R&D Expense               | FY            | SEC EDGAR     | Yahoo Finance |
|     | **Margins & Ratios**      |               |               |               |
| 15  | Gross Margin              | FY            | SEC EDGAR     | Yahoo Finance |
| 16  | Operating Margin          | FY            | SEC EDGAR     | Yahoo Finance |
| 17  | Net Margin                | FY            | SEC EDGAR     | Yahoo Finance |
| 18  | Debt to Equity            | Q             | SEC EDGAR     | Yahoo Finance |
| 19  | Revenue Growth (3yr CAGR) | FY            | SEC EDGAR     | Yahoo Finance |
|     | **Yahoo-Only Metrics**    |               |               |               |
| 20  | Return on Equity (ROE)    | Q             | Yahoo Finance | -             |
| 21  | Return on Assets (ROA)    | Q             | Yahoo Finance | -             |
| 22  | EBITDA Margin             | Q             | Yahoo Finance | -             |
| 23  | Current Ratio             | Q             | Yahoo Finance | -             |
| 24  | Quick Ratio               | Q             | Yahoo Finance | -             |
| 25  | Trailing EPS              | FY            | Yahoo Finance | -             |
| 26  | Forward EPS               | FY+1E         | Yahoo Finance | -             |
| 27  | Payout Ratio              | Q             | Yahoo Finance | -             |
| 28  | Revenue Growth (QoQ)      | Q             | Yahoo Finance | -             |
| 29  | Earnings Growth (QoQ)     | Q             | Yahoo Finance | -             |

### valuation-basket (17 metrics)

| S/N | metric                | temporal info | primary       | secondary     |
|-----|-----------------------|---------------|---------------|---------------|
|     | **Price & Size**      |               |               |               |
| 1   | Current Price         | Market Time   | Yahoo Finance | Alpha Vantage |
| 2   | Market Cap            | Market Time   | Yahoo Finance | Alpha Vantage |
| 3   | Enterprise Value      | Market Time   | Yahoo Finance | Alpha Vantage |
|     | **Earnings Multiples**|               |               |               |
| 4   | Trailing P/E          | Market Time   | Yahoo Finance | Alpha Vantage |
| 5   | Forward P/E           | Market Time   | Yahoo Finance | Alpha Vantage |
| 6   | Trailing PEG          | Market Time   | Yahoo Finance | Alpha Vantage |
| 7   | Forward PEG           | Market Time   | Yahoo Finance | Alpha Vantage |
|     | **Revenue Multiples** |               |               |               |
| 8   | P/S Ratio             | Market Time   | Yahoo Finance | Alpha Vantage |
| 9   | EV/Revenue            | Market Time   | Yahoo Finance | Alpha Vantage |
| 10  | EV/EBITDA             | Market Time   | Yahoo Finance | Alpha Vantage |
|     | **Asset Multiples**   |               |               |               |
| 11  | P/B Ratio             | Market Time   | Yahoo Finance | Alpha Vantage |
|     | **Risk**              |               |               |               |
| 12  | Beta                  | Market Time   | Yahoo Finance | Alpha Vantage |
|     | **Alpha Vantage Only**|               |               |               |
| 13  | 50 Day Moving Avg     | Market Time   | Alpha Vantage | -             |
| 14  | 200 Day Moving Avg    | Market Time   | Alpha Vantage | -             |
| 15  | 52 Week High          | Market Time   | Alpha Vantage | -             |
| 16  | 52 Week Low           | Market Time   | Alpha Vantage | -             |
| 17  | Analyst Target Price  | Market Time   | Alpha Vantage | -             |

### volatility-basket (5 metrics)

| S/N | metric                | temporal info | primary             | secondary     |
|-----|-----------------------|---------------|---------------------|---------------|
|     | **Market Indices**    |               |                     |               |
| 1   | VIX                   | Daily         | FRED                | Yahoo Finance |
| 2   | VXN                   | Daily         | FRED                | -             |
|     | **Stock-Specific**    |               |                     |               |
| 3   | Beta                  | 1yr rolling   | Yahoo Finance       | Alpha Vantage |
| 4   | Historical Volatility | 30-day        | Yahoo Finance       | Alpha Vantage |
| 5   | Implied Volatility    | ATM option    | Yahoo Finance Options| -            |

### macro-basket (4 metrics)

| S/N | metric             | temporal info | primary | secondary |
|-----|--------------------|---------------|---------|-----------|
| 1   | GDP Growth         | Quarterly     | BEA     | FRED      |
| 2   | CPI / Inflation    | Monthly       | BLS     | FRED      |
| 3   | Unemployment Rate  | Monthly       | BLS     | FRED      |
| 4   | Federal Funds Rate | Monthly       | FRED    | -         |

### news-basket (3 sources)

| S/N | metric        | temporal info | sources (collated)            |
|-----|---------------|---------------|-------------------------------|
| 1   | News Articles | Real-time     | Tavily + NYT + NewsAPI        |

### sentiment-basket (2 content sources)

| S/N | content      | temporal info | source  | note                              |
|-----|--------------|---------------|---------|-----------------------------------|
| 1   | Finnhub News | Real-time     | Finnhub | Raw articles, VADER applied downstream |
| 2   | Reddit Posts | Real-time     | Reddit  | Raw posts, VADER applied downstream   |

---

## Content Analysis: Source Cutoffs & Roles

### News Sources (news-basket)

| Source | Window | Delay | Role | Content Type | SWOT Value | Rate Limit |
|--------|--------|-------|------|--------------|------------|------------|
| Tavily | 7 days | Real-time | Breaking news, immediate coverage | Headlines, snippets | Identifies emerging threats/opportunities | API key required |
| NYT | 6 days | Real-time | Quality journalism, verified reporting | Full articles | Credible source for major events | Free tier available |
| NewsAPI | 7 days | 24hr | Analysis, opinion pieces, deep dives | Aggregated articles | Provides context after breaking news settles | 100 req/day (free) |

### Sentiment Sources (sentiment-basket)

| Source | Window | Delay | Role | Content Type | SWOT Value | Rate Limit |
|--------|--------|-------|------|--------------|------------|------------|
| Finnhub | 7 days | Real-time | Financial news, earnings coverage | Company news articles | Professional/institutional sentiment | Free tier available |
| Reddit | 7 days | Real-time | Consumer sentiment, retail investor views | Posts, discussions | Grassroots perception, emerging concerns | Public JSON endpoints |

### Temporal Strategy

The staggered timing creates complementary coverage:

```
T+0 hours    → Tavily, NYT, Finnhub (Breaking news)
T+24 hours   → NewsAPI (Analysis/opinion pieces)
T+1 to T+7   → Reddit (Consumer discussion develops)
```

**Rationale:**
- Breaking news captures immediate market-moving events
- Delayed analysis provides deeper context and expert opinions
- Consumer sentiment lags announcements as discussions develop organically
- 7-day window balances recency with sufficient volume

---

## API Endpoints

| S/N | Source        | Base URL                                            | API Key Required |
|-----|---------------|-----------------------------------------------------|------------------|
| 1   | SEC EDGAR     | `https://data.sec.gov/api/xbrl/`                    | No               |
| 2   | Yahoo Finance | `https://query1.finance.yahoo.com/`                 | No               |
| 3   | FRED          | `https://api.stlouisfed.org/fred/`                  | Yes (free)       |
| 4   | BEA           | `https://apps.bea.gov/api/data/`                    | Yes (free)       |
| 5   | BLS           | `https://api.bls.gov/publicAPI/v2/timeseries/data/` | Optional (free)  |
| 6   | Alpha Vantage | `https://www.alphavantage.co/query`                 | Yes (free tier)  |
| 7   | Tavily        | `https://api.tavily.com/`                           | Yes              |
| 8   | NYT           | `https://api.nytimes.com/`                          | Yes (free)       |
| 9   | NewsAPI       | `https://newsapi.org/v2/`                           | Yes (free tier)  |
| 10  | Finnhub       | `https://finnhub.io/api/v1/`                        | Yes (free tier)  |
| 11  | Reddit        | `https://oauth.reddit.com/`                         | Yes (OAuth)      |

---

## API Key Environment Variables

```bash
FRED_API_KEY=your_key
BEA_API_KEY=your_key
BLS_API_KEY=your_key
ALPHA_VANTAGE_API_KEY=your_key
TAVILY_API_KEY=your_key
NYT_API_KEY=your_key
NEWS_API_KEY=your_key
FINNHUB_API_KEY=your_key
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_key
```
