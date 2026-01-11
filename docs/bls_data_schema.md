BLS Data Schema
===============

Bureau of Labor Statistics API

Endpoint: https://api.bls.gov/publicAPI/v2/timeseries/data/
Method: POST with JSON payload


Series IDs

| series_id    | description                           |
|--------------|---------------------------------------|
| CUUR0000SA0  | CPI-U All Items (Consumer Price Index)|
| LNS14000000  | Unemployment Rate                     |


Request Payload

| field           | description                        |
|-----------------|------------------------------------|
| seriesid[]      | Array of BLS series IDs to fetch   |
| startyear       | Start year for data range          |
| endyear         | End year for data range            |
| registrationkey | Optional API key for higher limits |


Response Structure

| field           | description                       |
|-----------------|-----------------------------------|
| status          | REQUEST_SUCCEEDED or error code   |
| responseTime    | Response time in milliseconds     |
| message[]       | Array of status messages          |
| Results         | Results container                 |
| Results.series[]| Array of series data              |


Series Structure

| field    | description                 |
|----------|-----------------------------|
| seriesID | BLS series identifier       |
| data[]   | Array of observations       |


Observation Fields

| field      | description                                         |
|------------|-----------------------------------------------------|
| year       | 4-digit year (e.g., 2025)                           |
| period     | Period code (M01-M12 for monthly, A01 for annual)   |
| periodName | Human-readable period (January, February, etc.)     |
| value      | Data value as string                                |
| footnotes  | Array of footnote objects                           |


CPI-U All Items (CUUR0000SA0)

| field     | value                            |
|-----------|----------------------------------|
| series_id | CUUR0000SA0                      |
| title     | Consumer Price Index - All Items |
| units     | Index 1982-1984=100              |
| frequency | Monthly                          |
| period    | 2025-November                    |
| value     | 324.122                          |


Unemployment Rate (LNS14000000)

| field     | value             |
|-----------|-------------------|
| series_id | LNS14000000       |
| title     | Unemployment Rate |
| units     | Percent           |
| frequency | Monthly           |
| period    | 2025-December     |
| value     | 4.4               |


Period Codes

| code | description |
|------|-------------|
| M01  | January     |
| M02  | February    |
| M03  | March       |
| M04  | April       |
| M05  | May         |
| M06  | June        |
| M07  | July        |
| M08  | August      |
| M09  | September   |
| M10  | October     |
| M11  | November    |
| M12  | December    |
| A01  | Annual      |
