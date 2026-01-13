## Base URL
`https://api.stlouisfed.org/fred`

## Series Info Endpoint
`GET /series`

### Query Parameters
```
series_id
api_key
file_type   (json)
```

### Response Structure
```
seriess[]
  title
  units
  frequency
```

## Series Observations Endpoint
`GET /series/observations`

### Query Parameters
```
series_id
api_key
file_type    (json)
sort_order   (desc)
limit
```

### Response Structure
```
observations[]
  date
  value
```

## Series IDs Used

### Macro Basket
```
A191RL1Q225SBEA   (GDP growth rate)
FEDFUNDS          (Federal Funds Rate)
CPIAUCSL          (Consumer Price Index)
FPCPITOTLZGUSA    (Inflation rate)
UNRATE            (Unemployment Rate)
```

### Volatility Basket
```
VIXCLS            (VIX Index)
```
