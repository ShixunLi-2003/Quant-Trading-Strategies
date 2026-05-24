# Attribution Analysis

This folder explains where the strategy's realized performance comes from after portfolio construction and execution. It complements the factor-research section by answering a different question: once the strategy is live in simulation, which components, symbols, sides, and regimes actually drive PnL?

## Study Scope

- **Strategy context**: cross-sectional cryptocurrency long/short portfolio
- **Holding period**: 21 days
- **Sample window**: 2021-01-01 to 2026-03-20
- **Coverage snapshot from `strategy_summary.csv`**:
  - symbols covered: `512`
  - annualized return: `65.13%`
  - annualized volatility: `22.66%`
  - Sharpe ratio: `2.33`
  - maximum drawdown: `-12.61%`

## Core Tables

- `strategy_summary.csv`: headline portfolio statistics
- `component_time_series.csv`: time series for high-level PnL components
- `side_attribution_time_series.csv`: long, short, and net sleeve breakdown
- `symbol_attribution.csv`: contribution by symbol
- `monthly_attribution.csv`: monthly decomposition
- `yearly_attribution.csv`: yearly decomposition
- `offset_summary.csv`: contribution of different rebalance offsets
- `offset_nav_series.csv`: NAV path by offset sleeve
- `regime_summary.csv`: performance split by market regime
- `official_shadow_reconciliation.csv`: reconciliation diagnostics between portfolio views

## Chart Set

- Official vs Shadow NAV
- Long / Short / Net NAV
- Cumulative PnL Attribution
- Rolling Attribution Window
- Monthly Return Heatmap
- Top Symbol Contributors
- Bottom Symbol Contributors
- Offset Sleeve NAV
- Regime Annualized Return
- Exposure and Turnover
- NAV Gap

## How To Use This Folder

This section is particularly helpful when discussing:

- whether returns come mostly from the long side, the short side, or both
- whether PnL is diversified across many symbols or concentrated in a few names
- whether overlapping holding-period offsets smooth or destabilize the strategy
- whether strong headline performance survives reconciliation across reporting views

## Why This Matters In A Quant Interview

Strong backtest returns are rarely enough on their own. This attribution package is useful because it shows:

- return decomposition discipline
- exposure awareness
- sensitivity to portfolio construction details
- ability to explain not just that a strategy worked, but why it worked
