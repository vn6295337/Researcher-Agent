FRED Data Schema
================

Endpoint: https://api.stlouisfed.org/fred/series/observations


Raw API Response Structure
--------------------------

Series Info (seriess[0])

| field               | description                            |
|---------------------|----------------------------------------|
| id                  | Series identifier                      |
| title               | Series title                           |
| units               | Data units                             |
| frequency           | Update frequency (Daily, Monthly, etc) |
| seasonal_adjustment | Adjustment type (SA, NSA)              |
| last_updated        | Last update timestamp                  |

Observation (observations[])

| field          | description             |
|----------------|-------------------------|
| realtime_start | Real-time period start  |
| realtime_end   | Real-time period end    |
| date           | Observation date        |
| value          | Data value (string)     |


Series Data
-----------

GDP Growth (A191RL1Q225SBEA)

| field        | value                                |
|--------------|--------------------------------------|
| series_id    | A191RL1Q225SBEA                      |
| title        | Real Gross Domestic Product          |
| units        | Percent Change from Preceding Period |
| frequency    | Quarterly                            |
| date         | 2025-07-01                           |
| value        | 4.3                                  |
| last_updated | 2025-12-23 07:54:34                  |

Interest Rate (FEDFUNDS)

| field        | value                        |
|--------------|------------------------------|
| series_id    | FEDFUNDS                     |
| title        | Federal Funds Effective Rate |
| units        | Percent                      |
| frequency    | Monthly                      |
| date         | 2025-12-01                   |
| value        | 3.72                         |
| last_updated | 2026-01-02 15:18:33          |

CPI (CPIAUCSL)

| field        | value                                         |
|--------------|-----------------------------------------------|
| series_id    | CPIAUCSL                                      |
| title        | Consumer Price Index for All Urban Consumers  |
| units        | Index 1982-1984=100                           |
| frequency    | Monthly                                       |
| date         | 2025-11-01                                    |
| value        | 325.031                                       |
| last_updated | 2025-12-18 08:03:48                           |

Unemployment (UNRATE)

| field        | value               |
|--------------|---------------------|
| series_id    | UNRATE              |
| title        | Unemployment Rate   |
| units        | Percent             |
| frequency    | Monthly             |
| date         | 2025-12-01          |
| value        | 4.4                 |
| last_updated | 2026-01-09 08:10:37 |

VIX (VIXCLS)

| field        | value                      |
|--------------|----------------------------|
| series_id    | VIXCLS                     |
| title        | CBOE Volatility Index: VIX |
| units        | Index                      |
| frequency    | Daily, Close               |
| date         | 2026-01-08                 |
| value        | 15.45                      |
| last_updated | 2026-01-09 08:37:39        |

VXN (VXNCLS)

| field        | value                            |
|--------------|----------------------------------|
| series_id    | VXNCLS                           |
| title        | CBOE NASDAQ 100 Volatility Index |
| units        | Index                            |
| frequency    | Daily, Close                     |
| date         | 2026-01-08                       |
| value        | 20.15                            |
| last_updated | 2026-01-09 08:37:34              |


Time Categories
---------------
- Macro indicators (GDP, Interest Rate, CPI, Unemployment): date field is observation date
- Volatility indices (VIX, VXN): date field is market close date
