### Company Tickers Lookup
`GET https://www.sec.gov/files/company_tickers.json`

```
ticker
cik_str
```

### Company Facts (XBRL)
`GET https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`

## Response Structure

```
facts
  us-gaap
    {concept_name}
      units
        USD[]
          val
          end
          fy
          form
          filed
```

## Fields 

### Revenue
```
RevenueFromContractWithCustomerExcludingAssessedTax
Revenues
SalesRevenueNet
```
### Income Statement
```
NetIncomeLoss
GrossProfit
OperatingIncomeLoss
```
### Balance Sheet - Assets
```
Assets
```
### Balance Sheet - Liabilities
```
Liabilities
```
### Balance Sheet - Equity
```
StockholdersEquity
```
### Debt
```
LongTermDebt
LongTermDebtNoncurrent
ShortTermBorrowings
DebtCurrent
DebtAndCapitalLeaseObligations
LongTermDebtAndCapitalLeaseObligations
```
### Cash
```
CashAndCashEquivalentsAtCarryingValue
Cash
```
### Cash Flow
```
NetCashProvidedByUsedInOperatingActivities
PaymentsToAcquirePropertyPlantAndEquipment
```
### R&D
```
ResearchAndDevelopmentExpense
```
