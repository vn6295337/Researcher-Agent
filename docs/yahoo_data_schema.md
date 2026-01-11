Yahoo Finance Data Schema
=========================

Example: AAPL (Apple Inc)

Time Categories:
- Market Time: Real-time price data (regularMarketTime)
- Fiscal Time: Periodic accounting data (mostRecentQuarter, lastFiscalYearEnd)


Company Info

| field    | value              |
| -------- | ------------------ |
| longName | Apple Inc.         |
| address1 | One Apple Park Way |
| city     | Cupertino          |
| state    | CA                 |
| country  | United States      |


Valuation (Market Time: regularMarketTime)

| field               | value         |
|---------------------|---------------|
| regularMarketTime   | 1767992401    |
| marketCap           | 3832542658560 |
| enterpriseValue     | 3889336156160 |
| trailingPE          | 34.721554     |
| forwardPE           | 28.341707     |
| enterpriseToEbitda  | 26.87         |
| enterpriseToRevenue | 9.346         |
| priceToBook         | 51.967537     |


Margins, Returns & Growth (Fiscal Time: mostRecentQuarter)

| field                   | value      |
|-------------------------|------------|
| mostRecentQuarter       | 1758931200 |
| grossMargins            | 0.46905    |
| ebitdaMargins           | 0.34782    |
| operatingMargins        | 0.31647    |
| returnOnEquity          | 1.71422    |
| returnOnAssets          | 0.22964    |
| revenueGrowth           | 0.079      |
| earningsQuarterlyGrowth | 0.864      |


Earnings (Fiscal Time: lastFiscalYearEnd / earningsTimestamp)

| field             | value      |
|-------------------|------------|
| lastFiscalYearEnd | 1758931200 |
| trailingEps       | 7.47       |
| earningsTimestamp | 1769720400 |
| forwardEps        | 9.15153    |


Cash Flow & Liquidity/Debt (Fiscal Time: mostRecentQuarter)

| field             | value        |
|-------------------|--------------|
| mostRecentQuarter | 1758931200   |
| freeCashflow      | 78862254080  |
| operatingCashflow | 111482003456 |
| totalCash         | 54697000960  |
| currentRatio      | 0.893        |
| quickRatio        | 0.771        |
| debtToEquity      | 152.411      |
| totalDebt         | 112377004032 |


Risk (Market Time: regularMarketTime)

| field             | value      |
|-------------------|------------|
| regularMarketTime | 1767992401 |
| beta              | 1.093      |


Dividends (exDividendDate)

| field          | value      |
|----------------|------------|
| exDividendDate | 1762732800 |
| payoutRatio    | 0.1367     |
