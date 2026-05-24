# Factor Analysis Study

This folder contains the factor-research layer for the crypto strategy package. It is intended to answer a simple question: which candidate signals show stable cross-sectional forecasting power after basic liquidity screening and realistic portfolio formation rules?

## Study Scope

- **Strategy context**: cross-sectional cryptocurrency selection
- **Holding period**: 21 days
- **Sample window**: 2021-01-01 to 2026-03-20
- **Factors analyzed**: 7
- **Primary outputs**: summary tables, factor correlations, and per-factor diagnostic folders

## Main Deliverables

- `factor_summary.csv`: consolidated metrics for every tested factor
- `factor_summary.xlsx`: spreadsheet version for review
- `factor_correlation_matrix.csv`: pairwise relationship between tested signals
- per-factor folders: detailed charts and tables for each signal

## What Each Factor Folder Contains

Each factor directory includes a standard research pack:

- factor distribution profile
- Pearson IC time series
- Rank IC time series
- IC decay analysis
- monthly Rank IC heatmap
- signal-sorted forward return groups
- realized quantile portfolio NAV
- long-short portfolio NAV
- turnover diagnostics
- realized group statistics

## How To Read `factor_summary.csv`

The summary table is designed to separate signal quality from implementability.

- **IC metrics** such as `pearson_ic_mean`, `spearman_ic_mean`, and their Newey-West t-statistics measure forecasting strength
- **portfolio metrics** such as `portfolio_ann_return`, `portfolio_sharpe`, and `portfolio_max_drawdown` measure realized tradeability
- **turnover metrics** help judge whether the factor remains attractive after transaction frictions
- **monotonicity** helps verify whether the ranking signal behaves consistently across groups

## Current Snapshot Takeaways

Based on the current exported summary in this folder:

- `W42_(0.01, 0.99, True)` stands out as the strongest single selection factor in this research pack
- `QuoteVolumeMean_13` is useful as a conditioning or liquidity filter rather than as a directional alpha signal
- some candidates show weak or unstable realized portfolio performance despite having intuitive economic motivation
- the composite factor is positive, but the per-factor diagnostics remain important for understanding where the final portfolio edge comes from

## Why This Section Matters

For a quant interview, this folder is often more informative than the final equity curve alone because it shows:

- hypothesis testing discipline
- signal comparison rather than single-factor storytelling
- awareness of turnover and implementability
- robustness checks beyond headline return metrics
