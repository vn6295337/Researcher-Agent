Valuation Data Schema
=====================

Single source of truth for valuation-basket MCP server output.
Example: AAPL (Apple Inc)

| S/N | metric                | value      | temporal info   | source        |
|-----|-----------------------|------------|-----------------|---------------|
|     | **Price & Size**      |            |                 |               |
| 1   | Current Price         | $259.02    | Market Time     | Yahoo Finance |
| 2   | Market Cap            | $3.83T     | Market Time     | Yahoo Finance |
| 3   | Enterprise Value      | $3.89T     | Market Time     | Yahoo Finance |
|     | **Earnings Multiples**|            |                 |               |
| 4   | Trailing P/E          | 34.72x     | Market Time     | Yahoo Finance |
| 5   | Forward P/E           | 28.34x     | Market Time     | Yahoo Finance |
| 6   | Trailing PEG          | 2.64       | Market Time     | Yahoo Finance |
| 7   | Forward PEG           | 2.28       | Market Time     | Yahoo Finance |
|     | **Revenue Multiples** |            |                 |               |
| 8   | P/S Ratio             | 9.24x      | Market Time     | Yahoo Finance |
| 9   | EV/Revenue            | 9.35x      | Market Time     | Yahoo Finance |
| 10  | EV/EBITDA             | 26.88x     | Market Time     | Yahoo Finance |
|     | **Asset Multiples**   |            |                 |               |
| 11  | P/B Ratio             | 52.17x     | Market Time     | Yahoo Finance |
|     | **Risk**              |            |                 |               |
| 12  | Beta                  | 1.09       | Market Time     | Yahoo Finance |
|     | **Alpha Vantage Only**|            |                 |               |
| 13  | 50 Day Moving Avg     | $273.01    | Market Time     | Alpha Vantage |
| 14  | 200 Day Moving Avg    | $232.75    | Market Time     | Alpha Vantage |
| 15  | 52 Week High          | $288.62    | Market Time     | Alpha Vantage |
| 16  | 52 Week Low           | $168.63    | Market Time     | Alpha Vantage |
| 17  | Analyst Target Price  | $287.71    | Market Time     | Alpha Vantage |
