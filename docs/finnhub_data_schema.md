Finnhub Data Schema
===================

Endpoint: https://finnhub.io/api/v1/company-news
Method: GET


Request Parameters

| field  | type   | description             |
|--------|--------|-------------------------|
| symbol | string | Stock ticker            |
| from   | string | Start date (YYYY-MM-DD) |
| to     | string | End date (YYYY-MM-DD)   |
| token  | string | API key                 |


Response (array of articles)

| field    | type   | description      |
|----------|--------|------------------|
| headline | string | Article headline |
| summary  | string | Article summary  |
| url      | string | Article URL      |
| source   | string | Publisher name   |
| datetime | int    | Unix timestamp   |


Example Result

| field    | value                                |
|----------|--------------------------------------|
| headline | "Apple Reports Strong Q4 Earnings"   |
| summary  | "Apple Inc reported quarterly..."    |
| url      | "https://bloomberg.com/apple-q4..."  |
| source   | "Bloomberg"                          |
| datetime | 1736416200                           |
