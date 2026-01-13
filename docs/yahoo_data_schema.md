## yfinance Library (Ticker.info)

### Valuation Fields
```
currentPrice
regularMarketPrice
marketCap
enterpriseValue
trailingPE
forwardPE
priceToSalesTrailing12Months
priceToBook
enterpriseToEbitda
trailingPegRatio
earningsGrowth
revenueGrowth
```
### Fundamentals Fallback Fields
```
totalRevenue
netIncomeToCommon
grossProfits
operatingIncome
ebitda
totalCash
totalDebt
freeCashflow
operatingCashflow
operatingMargins
profitMargins
debtToEquity
longName
shortName
sector
industry
```
## Chart API

### Endpoint
`GET https://query1.finance.yahoo.com/v8/finance/chart/{ticker}`
### Query Parameters
```
interval   (1d)
range      (1y, 3mo, 5d, 1d)
```
### Response Structure
```
chart
  result[]
    meta
      regularMarketPrice
      previousClose
    indicators
      quote[]
        close[]
```
## Options API
### Endpoint
`GET https://query1.finance.yahoo.com/v7/finance/options/{ticker}`
### Response Structure
```
optionChain
  result[]
    options[]
      calls[]
        strike
        impliedVolatility
```
