# Research Results

[Cantonese version](README.yue.md)

## Figures

| File | Content |
|---|---|
| `research_workflow.png` | End-to-end research architecture and cross-cutting controls |
| `factor_information_coefficients.png` | Mean daily Rank IC for all 16 factors |
| `factor_quantile_bins.png` | Terminal return across five composite-score bins |
| `factor_quantile_nav.png` | Quantile and long-short diagnostic NAV |
| `factor_ic_robustness.png` | Development and holdout composite IC with Newey-West intervals |
| `factor_nonoverlap_quantiles.png` | Non-overlapping three-session returns across selected-score bins |
| `strict_backtest_equity_curves.png` | Baseline versus tuned strategy under strict costs |
| `rolling_window_returns.png` | Twenty-period rolling compounded returns |
| `exit_time_sensitivity.png` | Total return across scheduled minute exits |
| `scheduled_1453_equity_curve.png` | Selected 14:53 minute-execution NAV |
| `model_holdout_comparison.png` | Ridge, random-forest, and neural-network holdout returns |
| `etf_overlay_oos_comparison.png` | No-overlay, fixed-overlay, and adaptive-overlay OOS returns |
| `etf_overlay_continuous_oos_equity.png` | Adaptive ETF continuous OOS NAV |
| `matched_period_benchmark_comparison.png` | Adaptive strategy versus five ETF benchmarks over the actual common interval |

## Core Tables

| File | Purpose |
|---|---|
| `public_headline_metrics.csv` | Compact source for the headline result table |
| `factor_ic_robustness.csv` | Full, development, and holdout IC with HAC inference |
| `composite_nonoverlap_quantiles.csv` | Three independent calendar sleeves for the selected score |
| `strict_stress_current_vs_tuned.csv` | Baseline and tuned strategy under strict costs |
| `strict_tuned_rolling_20periods.csv` | Rolling stability of the selected 60/40 blend |
| `scheduled_exit_minute_comparison.csv` | Minute exit-time sensitivity and execution availability |
| `etf_regime_nested_summary.csv` | Six-fold nested ETF selection summary |
| `etf_regime_continuous_oos.csv` | Continuous adaptive, fixed, and no-overlay comparison |
| `matched_period_benchmark_comparison.csv` | Strategy and five market benchmarks over the common interval |
| `public_model_holdout_comparison.csv` | Holdout comparison of the three machine-learning families |

## Extended Audit Trail

The remaining tables preserve tuning grids, period-level NAV, model-family outputs, ETF sensitivity, nested selections, holding distributions, and archived comparisons. They are retained for traceability but are not required to understand the main conclusion. `example_trade_schema.csv` documents the anonymized trade-output format.

Raw market data, security-level backtest records, and live account records are excluded.

Regenerate figures and summary tables with:

```bash
python scripts/generate_report_assets.py
```
