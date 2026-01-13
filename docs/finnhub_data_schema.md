## Company News Endpoint
`GET https://finnhub.io/api/v1/company-news`

## Request Parameters
```
symbol
from      (YYYY-MM-DD)
to        (YYYY-MM-DD)
token
```

## Response Structure
```
[]
  headline
  summary
  url
  source
  datetime    (Unix timestamp)
```
