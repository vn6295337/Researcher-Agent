Yahoo Finance Options Data Schema
==================================

Example: AAPL (Apple Inc)

Endpoint: https://query1.finance.yahoo.com/v7/finance/options/{ticker}


Response Structure

| field                  | description                         |
|------------------------|-------------------------------------|
| optionChain            | Root container for options data     |
| optionChain.result     | Array of result objects             |
| result[0].quote        | Underlying stock quote data         |
| result[0].options      | Array of options by expiration      |
| result[0].strikes      | Available strike prices             |
| result[0].expirationDates | Unix timestamps of expirations   |


quote (Underlying Stock)

| field                     | description               |
|---------------------------|---------------------------|
| symbol                    | Ticker symbol             |
| regularMarketPrice        | Current stock price       |
| regularMarketTime         | Quote timestamp (Unix)    |
| regularMarketChange       | Price change              |
| regularMarketChangePercent| Price change percentage   |


Expiration Dates

| field           | description                           |
|-----------------|---------------------------------------|
| expirationDates | Array of Unix timestamps              |
| count           | Number of available expiration dates  |
| first           | Nearest expiration (Unix timestamp)   |
| last            | Furthest expiration (Unix timestamp)  |


Strike Prices

| field   | description                  |
|---------|------------------------------|
| strikes | Array of available strikes   |
| count   | Number of strike prices      |
| min     | Lowest available strike      |
| max     | Highest available strike     |


options[0] (First Expiration)

| field          | description                      |
|----------------|----------------------------------|
| expirationDate | Expiration date (Unix timestamp) |
| calls[]        | Array of call option contracts   |
| puts[]         | Array of put option contracts    |


Contract Fields (calls[] / puts[])

| field             | description                        |
|-------------------|------------------------------------|
| contractSymbol    | Option contract symbol             |
| strike            | Strike price                       |
| currency          | Currency (USD)                     |
| lastPrice         | Last traded price                  |
| change            | Price change                       |
| percentChange     | Price change percentage            |
| volume            | Trading volume                     |
| openInterest      | Open interest                      |
| bid               | Bid price                          |
| ask               | Ask price                          |
| impliedVolatility | Implied volatility (decimal, 0-1+) |
| inTheMoney        | Boolean: in the money              |
| expiration        | Expiration timestamp               |
| lastTradeDate     | Last trade timestamp               |


Implied Volatility Extraction
-----------------------------

To get ATM implied volatility:
1. Get regularMarketPrice from quote
2. Find call with strike closest to current price
3. Read impliedVolatility field (multiply by 100 for %)

Example:

| field                   | value   |
|-------------------------|---------|
| currentPrice            | 259.02  |
| atmStrike               | 260.00  |
| impliedVolatility (raw) | 0.2845  |
| impliedVolatility (%)   | 28.45%  |
