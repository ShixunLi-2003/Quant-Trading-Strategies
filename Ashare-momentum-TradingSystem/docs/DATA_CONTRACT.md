# Data Contract

## Daily Table

| Column | Type | Definition |
|---|---|---|
| `stock_code` | string | Exchange-qualified security identifier |
| `trade_date` | date | China-market trading date |
| `open`, `high`, `low`, `close` | float | Adjusted or consistently unadjusted prices |
| `volume` | float | Shares or lots, used consistently across the dataset |
| `amount` | float | Turnover amount |

## Minute Table

| Column | Type | Definition |
|---|---|---|
| `stock_code` | string | Exchange-qualified security identifier |
| `datetime` | timestamp | UTC timestamp convertible to `Asia/Shanghai` |
| `open`, `high`, `low`, `close` | float | One-minute OHLC |
| `volume` | float | One-minute volume |
| `amount` | float | One-minute turnover amount |

## Universe Membership

Point-in-time membership requires `stock_code`, `effective_from`, and `effective_to`. A row is eligible only when its signal date falls inside the membership interval. A latest-only universe must be labeled as fallback and must not be described as survivorship-bias free.

## Excluded Public Data

Vendor market files, broker state, account identifiers, order logs, machine paths, and credentials are excluded from the repository.

