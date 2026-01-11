SEC EDGAR Data Schema
=====================

Example: AAPL (Apple Inc) - CIK 0000320193

Raw field meanings:

| Field | Description                       |
|-------|-----------------------------------|
| val   | Raw value (in USD)                |
| end   | Period end date                   |
| fy    | Fiscal year                       |
| fp    | Fiscal period (FY, Q1, Q2, Q3)    |
| form  | Filing type (10-K, 10-Q)          |
| filed | Filing date                       |
| accn  | SEC accession number              |
| frame | Calendar frame (CY2025, CY2025Q2) |

Common fields (same across all metrics):

| Field | Value                |
|-------|----------------------|
| end   | 2025-09-27           |
| fy    | 2025                 |
| fp    | FY                   |
| form  | 10-K                 |
| filed | 2025-10-31           |
| accn  | 0000320193-25-000079 |


Metrics
-------

Income Statement

| name             | val          | frame  |
|------------------|--------------|--------|
| revenue          | 416161000000 | CY2025 |
| gross_profit     | 195201000000 | CY2025 |
| operating_income | 133050000000 | CY2025 |
| net_income       | 112010000000 | CY2025 |

Balance Sheet

| name                | val          | frame     |
|---------------------|--------------|-----------|
| total_assets        | 359241000000 | CY2025Q3I |
| cash                | 35934000000  | CY2025Q3I |
| total_liabilities   | 285508000000 | CY2025Q3I |
| long_term_debt      | 90678000000  | CY2025Q3I |
| stockholders_equity | 73733000000  | CY2025Q3I |

Cash Flow

| name                | val          | frame  |
|---------------------|--------------|--------|
| operating_cash_flow | 111482000000 | CY2025 |
| capital_expenditure | 12715000000  | CY2025 |

Expenses

| name       | val         | frame  |
|------------|-------------|--------|
| rd_expense | 34550000000 | CY2025 |
