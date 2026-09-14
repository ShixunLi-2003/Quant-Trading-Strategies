# Research Quality Assessment

## Verdict

The repository is suitable for a quantitative-research or research-engineering portfolio. It demonstrates a complete decision trail, realistic execution constraints, explicit failure cases, and reproducible aggregate evidence. The current results are promising but do not justify describing the strategy as proven, production-grade, or persistently alpha-generating.

## Factor Evidence

The defensive low-volatility score is the clearest signal. Across 293 dates, its mean daily Rank IC is 0.0474 and its Newey-West t-statistic is 3.59. The selected 60% defensive and 40% broad-momentum blend has mean IC 0.0316 and t-statistic 2.71. In the 109-date holdout, the selected blend improves to mean IC 0.0551 with t-statistic 2.43.

The non-overlapping holdout quantile test is directionally strong: all three calendar sleeves show positive Q5-Q1 spreads and quantile monotonicity of 0.9, 0.9, and 1.0. Individual spread t-statistics range from 1.16 to 1.52, below the conventional two-sided 5% threshold. This supports economic relevance but not high-confidence standalone significance.

Several individual trend factors change sign between development and holdout. The stable components are primarily late-session reversal, low realized volatility, low amplitude, VWAP reversion, and early-session strength. This is better described as a defensive intraday reversal blend than as pure momentum.

## Portfolio Evidence

The strict tuned candidate earns 28.87% over 97 periods under 30 bps adverse slippage on both entry and exit, but its locked holdout earns only 6.09% with a 20.77% maximum drawdown. Across 78 rolling windows of 20 periods, 71.8% are positive; the median return is 7.25%, while the worst is -16.60%.

The minute-execution and adaptive ETF results begin on 2025-12-25, not 2025-07-02. Over the actual common interval, the adaptive strategy earns 34.10% with an 8.02% drawdown. Five ETF benchmarks return between -3.07% and 17.76%, so the strategy is above all selected benchmarks in this sample. The evidence is not long enough to establish persistence.

The adaptive ETF process compounds to 29.20% across six nested test folds, compared with 12.28% for no overlay. Only three of six adaptive folds are positive. The continuous result is therefore driven by uneven fold outcomes rather than uniformly positive performance.

## Evidence Grade

| Area | Grade | Rationale |
|---|---|---|
| Repository engineering | Strong | Modular code, tests, data contracts, CI, manifests, and safety controls |
| Factor plausibility | Moderate to strong | Economically coherent defensive signal with HAC-adjusted significance |
| Cross-sectional robustness | Moderate | Positive holdout ordering, but limited non-overlapping observations |
| Cost and execution realism | Moderate to strong | Board lots, fees, slippage, minute availability, and delayed exits are modeled |
| Out-of-sample evidence | Moderate | Locked holdout and nested tests exist, but samples are short |
| Universe integrity | Weak to moderate | Historical point-in-time membership is unavailable for key archived runs |
| Live-readiness evidence | Preliminary | Research simulation only; no audited live track record |

## Minimum Evidence Before a Strong Alpha Claim

1. Rebuild every headline run with dated point-in-time universe snapshots.
2. Extend minute and ETF history across at least one additional bull, bear, and sideways regime.
3. Freeze the current specification and collect six to twelve months of untouched forward results.
4. Report turnover, capacity, liquidity participation, sector exposure, beta, and factor attribution.
5. Add bootstrap confidence intervals and a multiple-testing adjustment for the research search path.
