# Limitations and Interpretation

1. **Universe history:** several archived tables contain `pool_pit_mode=latest_fallback` and `pool_snapshot_count=0`. They are useful for engineering comparison but may contain survivorship bias.
2. **Sample length:** the usable minute-execution and continuous ETF OOS sample starts on 2025-12-25 and contains 57 portfolio periods. It does not span enough market cycles for a definitive risk estimate.
3. **Selection risk:** factor weights, sector thresholds, exit time, and ETF parameters were compared across multiple candidates. Holdout and nested tests reduce but do not eliminate selection bias.
4. **Approximate annualization:** reported annualized returns and Sharpe ratios extrapolate short-horizon observations and should not be interpreted as long-run forecasts.
5. **Market microstructure:** minute bars cannot reproduce queue priority, partial fills, cancellations, or intrabar price paths.
6. **Corporate actions:** input prices must use a consistent adjustment convention. Mixing adjusted and unadjusted series invalidates returns.
7. **Live transferability:** public results are research simulations, not audited brokerage performance.
8. **Benchmark scope:** matched ETF comparisons show relative performance only for the observed interval. They do not control for factor exposures, changing beta, or benchmark-selection bias.

The strongest evidence is the defensive factor's HAC-adjusted IC, positive holdout quantile ordering, and directionally consistent improvement across strict costs and ETF controls. The weakest evidence is the 57-period minute sample, only six nested ETF folds, and missing historical universe snapshots in archived runs.
