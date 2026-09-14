# Methodology

## Signal Timing

Daily and minute features for date `t` are used to rank candidates for the next executable session. Forward returns are labels only. Model training applies a three-session embargo for a three-session target to prevent overlapping labels from leaking into the test date.

## Factor Set

The factor panel contains three groups:

- Daily momentum and trend: 1-, 3-, and 5-day returns; distance to 5- and 20-day moving averages.
- Daily activity and range: one-day amplitude and five-day amount ratio.
- Intraday structure: full-session, first-30-minute, first-60-minute, and last-30-minute returns; close location; realized volatility; positive-minute ratio; late-session amount share; and VWAP distance.

Daily cross-sectional z-scores make factors comparable. The defensive score reverses late-session return, realized volatility, daily amplitude, and VWAP distance while retaining early-session strength. The selected blend assigns 60% to this defensive component and 40% to the broad momentum composite.

## Factor Validation

Each factor is evaluated using daily Spearman Rank IC against the three-session forward return. The report includes mean IC, IC volatility, IC information ratio, positive-IC frequency, and sample count. Because three-session labels overlap, significance is reported with a Newey-West covariance estimate using a three-lag Bartlett kernel. Composite scores are also tested in three non-overlapping calendar sleeves. Composite scores are sorted into five equal-count portfolios each date. The legacy daily quantile NAV compounds overlapping labels and is therefore a diagnostic, not the executable portfolio result; the non-overlapping quantile table is the preferred robustness check.

## Model Comparison

Ridge regression, random forest, and multilayer perceptron models use rolling training windows. Targets are cross-sectionally demeaned and winsorized. The test date is never included in training. Complex models were retained in the report even when they underperformed; this avoids presenting only successful experiments.

## Executable Backtest

The executable simulation applies:

- 100-share board lots;
- minimum commission;
- buy and sell commission;
- sell-side stamp duty;
- adverse buy and sell slippage;
- price and board eligibility checks;
- finite capital and unused cash;
- one-minute entry and scheduled exit prices;
- unavailable-bar and delayed-exit accounting.

The strict stress test uses 30 bps adverse slippage on both sides. The selected scheduled exit is 14:53, chosen from a narrow pre-declared range rather than an unrestricted minute search.

## ETF Regime Overlay

ETF closing prices are converted into trend breadth and return summaries. Exposure for session `t+1` is computed after session `t`, preventing same-session look-ahead. Weak breadth must persist before exposure is reduced. Candidate scopes and thresholds are evaluated with nested rolling windows and a continuous out-of-sample sequence.

## Benchmark Comparison

The continuous out-of-sample strategy is compared with broad-market and growth-style ETF close series over the actual common interval, not the originally requested backtest range. Benchmark returns are unlevered buy-and-hold close-to-close returns and exclude trading costs, which gives the passive benchmarks a conservative advantage. The comparison supports only a matched-sample statement; it is not a factor alpha regression or a long-run performance attribution.

## Execution Safety

The execution layer records broker inventory before each strategy buy. Existing shares form a protected manual floor. Reconciliation attributes only the incremental shares to the strategy, and every sell path is capped by both broker sellable quantity and strategy-managed quantity.
