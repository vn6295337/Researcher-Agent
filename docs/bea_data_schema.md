BEA Data Schema
===============

Bureau of Economic Analysis - NIPA (National Income and Product Accounts)

Endpoint: https://apps.bea.gov/api/data
Dataset: NIPA
Table: T10101 (Percent Change From Preceding Period in Real GDP)


Request Parameters

| field        | description                         |
|--------------|-------------------------------------|
| UserID       | API key (required)                  |
| method       | GetData                             |
| datasetname  | NIPA                                |
| TableName    | T10101 (GDP percent change)         |
| Frequency    | Q (Quarterly) or A (Annual)         |
| Year         | X (all years) or specific year      |
| ResultFormat | JSON                                |


Response Structure

| field                     | description                 |
|---------------------------|-----------------------------|
| BEAAPI                    | Root container              |
| BEAAPI.Request            | Echo of request parameters  |
| BEAAPI.Results            | Results container           |
| Results.Statistic         | Data type (NIPA Table)      |
| Results.UTCProductionTime | Timestamp of data generation|
| Results.Notes[]           | Array of data notes         |
| Results.Data[]            | Array of data observations  |


Data Row Fields

| field           | description                                       |
|-----------------|---------------------------------------------------|
| TableName       | NIPA table identifier (T10101)                    |
| SeriesCode      | BEA series code for the metric                    |
| LineNumber      | Row number in the table (1 = Real GDP)            |
| LineDescription | Human-readable metric name                        |
| TimePeriod      | Time period (YYYYQN format, e.g., 2025Q3)         |
| METRIC_NAME     | Metric type (e.g., Fisher Quantity Index)         |
| CL_UNIT         | Unit description (Percent change, annual rate)    |
| UNIT_MULT       | Unit multiplier                                   |
| DataValue       | The actual data value                             |
| NoteRef         | Reference to notes array                          |


GDP Data (LineNumber = 1)

| TimePeriod | DataValue | LineDescription        |
|------------|-----------|------------------------|
| 2025Q3     | 4.3       | Gross domestic product |
| 2025Q2     | 3.8       | Gross domestic product |
| 2025Q1     | -0.6      | Gross domestic product |
| 2024Q4     | 1.9       | Gross domestic product |
| 2024Q3     | 3.3       | Gross domestic product |
| 2024Q2     | 3.6       | Gross domestic product |


Line Numbers Reference

| LineNumber | Description                           |
|------------|---------------------------------------|
| 1          | Gross domestic product                |
| 2          | Personal consumption expenditures     |
| 7          | Gross private domestic investment     |
| 11         | Net exports of goods and services     |
| 22         | Government consumption expenditures   |
