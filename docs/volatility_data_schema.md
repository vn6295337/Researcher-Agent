Volatility Data Schema
======================

Single source of truth for volatility-basket MCP server output.
Example: AAPL (Apple Inc)

| S/N | metric                | value   | temporal info | source              |
|-----|-----------------------|---------|---------------|---------------------|
|     | **Market Indices**    |         |               |                     |
| 1   | VIX                   | 15.45   | 2026-01-08    | FRED                |
| 2   | VXN                   | 20.15   | 2026-01-08    | FRED                |
|     | **Stock-Specific**    |         |               |                     |
| 3   | Beta                  | 1.29    | 1yr rolling   | Yahoo Finance       |
| 4   | Historical Volatility | 12.33%  | 30-day        | Yahoo Finance       |
| 5   | Implied Volatility    | 28.45%  | ATM option    | Yahoo Finance Options|
