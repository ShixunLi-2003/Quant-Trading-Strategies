# Resume Notes

## Concise Version

- Built an end-to-end A-share short-horizon research system using daily and one-minute data, 16 cross-sectional factors, Rank IC diagnostics, quantile portfolios, and walk-forward model validation.
- Implemented a cost-aware portfolio simulator with board lots, minimum commission, stamp duty, adverse slippage, minute-level execution, holdout tests, rolling windows, and nested ETF regime controls.
- Designed live position-ownership reconciliation that separates strategy inventory from pre-existing manual holdings and caps every sell path at strategy-managed quantity.

## Interview Topics

- Why a defensive low-volatility blend outperformed tree and neural models in the available sample.
- How embargoed walk-forward validation differs from random train/test splitting.
- Why quantile NAV is a factor diagnostic rather than an executable capital curve.
- How ETF breadth can reduce drawdown without using same-day information.
- How missing historical universe snapshots create survivorship bias.

