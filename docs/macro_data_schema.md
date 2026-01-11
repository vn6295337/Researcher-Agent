Macro Economic Data Schema
==========================

Single source of truth for macro-basket MCP server output.

| S/N | metric            | value | temporal info | source |
|-----|-------------------|-------|---------------|--------|
| 1   | GDP Growth        | 4.3%  | Q3 2025       | BEA    |
| 2   | CPI / Inflation   | 2.74% | Nov 2025      | BLS    |
| 3   | Unemployment Rate | 4.4%  | Dec 2025      | BLS    |
| 4   | Federal Funds Rate| 3.72% | Dec 2025      | FRED   |


Source Hierarchy
----------------

| metric            | primary | fallback |
|-------------------|---------|----------|
| GDP Growth        | BEA     | FRED     |
| CPI / Inflation   | BLS     | FRED     |
| Unemployment Rate | BLS     | FRED     |
| Federal Funds Rate| FRED    | -        |
