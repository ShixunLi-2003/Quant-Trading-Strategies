# A-Share Dynamic Mean Reversion & Multi-Factor Flow Alpha (DMR-MFA)

## Project Overview

`DMR-MFA` is an A-share active trading research system built around dynamic exposure control, oversold rebound capture, main-capital-flow confirmation, and technical exit refinement.

Rather than relying on a single timing rule, the strategy combines several layers:

- benchmark Bollinger-band regime detection
- dynamic holding-capacity adjustment
- oversold rebound entry logic
- positive net-main-inflow filtering
- OBV divergence profit protection
- BBI deterioration-based defensive exits

Taken together, the project is best described as a dynamic mean-reversion framework with active exposure management and execution-aware exit control.

## Interview Snapshot

### Key Results

- `2011-2026`: annualized return `56.87%`, Sharpe `1.561`, max drawdown `26.66%`
- `2014-2015` bull/volatile window: annualized return `151.34%`
- `2018` bear market window: strategy `10.76%` versus benchmark `-25.31%`
- stronger upside elasticity than A-share 1, with materially higher volatility and drawdown

### Why It's Credible

- has a clear economic identity: oversold rebound capture gated by positive main-capital flow and explicit exits
- preserves multi-window backtests, attribution outputs, raw holdings, and trade records
- includes broad stability evidence around regime thresholds, holding capacity, exit floors, and transaction costs
- modular implementation separates regime, entry, exit, and execution logic for inspection

### Main Risks

- fixed stock pool is a real research assumption and must be treated as one
- ST, limit-state, and newly listed stock filtering are not yet fully explicit in the production path
- the strategy is more implementation-sensitive than A-share 1 because turnover, thresholds, and exits matter more

## Strategy Logic

### 1. Market regime layer

The strategy uses `000300.XSHG` as the benchmark and measures its Bollinger-band position to classify market conditions.

That regime signal controls target holding capacity rather than only flipping a binary long or flat switch.

Default capacity settings are organized around:

- low-capacity defensive mode
- neutral-capacity base mode
- high-capacity offensive mode

This makes the strategy an exposure-adjusting alpha system rather than a static stock screener.

### 2. Entry layer

The offensive logic is built on three main ideas:

- a stock should already be under medium-short weakness pressure
- it should also show a sharper recent drawdown
- and the rebound candidate should be supported by positive main-capital flow

In practical terms, the strategy searches a fixed pool for names that satisfy:

- a lookback-based downtrend condition
- a recent drawdown threshold
- positive `net_amount_main`

Qualifying names are then ranked and deployed through equal-cash-style position allocation subject to the active-capacity regime.

### 3. Exit layer

The sell-side logic combines:

- hard take-profit
- hard stop-loss
- OBV-based early profit protection
- BBI-slope deterioration exits

This gives the strategy several ways to monetize rebounds while trying to cut weak follow-through efficiently.

## Repository Structure

```text
2.A-Share Dynamic Mean Reversion & Multi-Factor Flow Alpha (DMR-MFA)/
|- Code/
|- Factor Analysis/
|- Backtest-Raw-Results/
|- Attribution Analysis/
|- Result_Images/
|- Stability/
|- REPRODUCIBILITY.md
`- README.md
```

### `Code`

The implementation layer.

- `Complete_code.py`
  The JoinQuant-facing entry script.
- `modular_dmr_mfa/`
  The modularized implementation of regime detection, portfolio construction, and risk-control logic.

### `Factor Analysis`

The research layer that documents how the underlying building blocks were inspected before strategy integration.

This includes notebooks for:

- benchmark Bollinger regime behavior
- downtrend logic
- drawdown logic
- money-flow filtering
- OBV divergence
- BBI slope
- cross-factor diagnostics

### `Backtest-Raw-Results`

The raw result layer that stores:

- performance summary tables
- daily holdings and exposure data
- trade execution details
- multiple backtest windows

### `Attribution Analysis`

The audit layer used to inspect:

- return decomposition
- style and risk exposure
- position contribution
- trading behavior
- drawdown structure
- slippage and implementation sensitivity

### `Result_Images`

The visual summary layer for fast inspection of major backtest results.

### `Stability`

The robustness-validation layer.

This directory now preserves a standardized archive of parameter and stress tests. Each subfolder contains:

- `benefits_overview.png`
- `daily_holdings_and_exposure.csv`
- `daily_performance_comparison.csv`
- `trade_execution_details.csv`

## Performance Profile

## Final Performance Summary

The archived final backtest summary from `Backtest-Raw-Results/Performance_Summary.csv` is shown below.

| Backtest Period | Strategy Annualized Return | Benchmark Return (CSI 300) | Alpha | Beta | Sharpe Ratio | Sortino Ratio | Information Ratio | Max Drawdown | Profit/Loss Ratio | Winning Rate | Strategy Volatility |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2011-2026 (Long Term) | 56.87% | 52.46% | 0.536 | 0.663 | 1.561 | 2.414 | 1.707 | 26.66% | 1.862 | 0.556 | 0.339 |
| 2014-2015 (Bull/Volatile) | 151.34% | 60.13% | 1.325 | 0.637 | 3.381 | 5.071 | 3.068 | 31.04% | 2.670 | 0.692 | 0.436 |
| 2018 (Bear Market) | 10.76% | -25.31% | 0.275 | 0.694 | 0.176 | 0.282 | 1.018 | 22.72% | 1.177 | 0.389 | 0.384 |
| 2022-2024 (Sideways/Down) | 33.87% | -20.35% | 0.376 | 0.672 | 0.921 | 1.584 | 1.356 | 21.14% | 1.588 | 0.472 | 0.324 |
| 2024-2026 (Recent) | 40.16% | 38.68% | 0.268 | 0.801 | 1.040 | 1.612 | 0.769 | 23.31% | 1.826 | 0.465 | 0.348 |

## Key Takeaways

- The strategy is clearly a high-elasticity system: upside in favorable environments is strong, but the path of returns is materially more aggressive than a lower-beta enhancement strategy.
- Performance remains positive in weak benchmark environments, which suggests the rebound-and-flow logic is not purely a bull-market artifact.
- The strongest upside appears in volatile and opportunistic phases, while the main trade-off is larger drawdown and volatility versus the cross-factor strategy.
- The key implementation risks are capacity-setting sensitivity, threshold tuning, and trading-cost dependence, which is why the `Stability` archive is central to evaluating the system.

Based on the archived summary tables, the strategy exhibits:

- strong return elasticity in favorable environments
- meaningful long-term alpha generation
- preserved offensive behavior in bullish phases
- nontrivial but still interpretable drawdown risk
- a clear dependence on execution cost, signal thresholds, and capacity controls

The table shows why `DMR-MFA` should be treated as a high-elasticity active strategy rather than a low-volatility enhancement model. The upside is substantial in favorable regimes, but the path of returns remains materially more aggressive than that of the cross-factor strategy.

That profile is exactly why the strategy needs a serious stability layer rather than only headline performance charts.

## Stability and Robustness Coverage

The current `Stability` directory already captures a broad first-pass robustness archive for the strategy.

It includes tests around:

- benchmark Bollinger window sensitivity
- benchmark Bollinger standard-deviation multiplier sensitivity
- downtrend lookback sensitivity
- drawdown-trigger sensitivity
- dynamic holding-capacity sensitivity
- stop-loss and take-profit threshold sensitivity
- OBV and BBI exit-floor sensitivity
- transaction-cost stress
- stock-pool variation

Representative folders include:

- `benchmark_bollinger_window_20_to_15_2011_2026`
- `benchmark_bollinger_window_20_to_30_2011_2026`
- `benchmark_bollinger_std_multiplier_2_to_1_5_2011_2026`
- `benchmark_bollinger_std_multiplier_2_to_2_5_2011_2026`
- `holding_capacity_3_5_7_to_2_4_6_2011_2026`
- `holding_capacity_3_5_7_to_4_6_8_2011_2026`
- `downtrend_lookback_10_to_8_2011_2026`
- `downtrend_lookback_10_to_12_2011_2026`
- `downtrend_lookback_10_to_15_2011_2026`
- `drawdown_trigger_minus_0_07_to_minus_0_05_2011_2026`
- `drawdown_trigger_minus_0_07_to_minus_0_09_2011_2026`
- `take_profit_0_15_to_0_12_and_stop_loss_minus_0_035_to_minus_0_03_2011_2026`
- `take_profit_0_15_to_0_18_and_stop_loss_minus_0_035_to_minus_0_04_2011_2026`
- `obv_profit_floor_0_01_to_0_005_and_bbi_drawdown_floor_minus_0_03_to_0_02_2011_2026`
- `obv_profit_floor_0_01_to_0_02_and_bbi_drawdown_floor_minus_0_03_to_minus_0_04_2011_2026`
- `slippage_0_002_to_0_005_2011_2026`
- `slippage_0_002_to_0_01_2011_2026`
- `commission_0_0003_to_0_00045_2011_2026`
- `stock_pool_variant_2011_2026`

## Why the Stability Layer Matters

This strategy is intentionally aggressive and high-elasticity. That means strong reported returns alone are not enough.

The main research questions become:

- Is the rebound logic robust to parameter perturbation?
- Is alpha still present when transaction costs rise?
- Does the strategy remain coherent when capacity rules change?
- Is performance dependent on one narrow stock-pool specification?
- Are exits economically meaningful or overly tuned?

The `Stability` directory exists to answer those questions with archived evidence rather than intuition.

## Why This Is More Than Curve Fitting

This project is easier to overstate than the first A-share strategy because the return profile is more aggressive. For that reason, the right claim is not "it cannot be overfit," but "the repository contains evidence that lets a reviewer challenge it seriously."

Evidence that goes beyond a single tuned result includes:

- the strategy has a clear economic identity: oversold rebound capture gated by positive main-capital flow and explicit exit logic
- results are archived across multiple market windows rather than only the strongest bull period
- the `Stability` layer perturbs regime thresholds, holding capacity, drawdown triggers, exit floors, and transaction costs
- attribution and raw trade artifacts are preserved so the path of returns can be inspected rather than only summarized
- the modular implementation makes regime, entry, exit, and execution logic reviewable in separate components

The honest limitations are equally important:

- the fixed stock pool is itself a research assumption and should be treated as such
- the current version still needs stricter summary evidence around anti-lookahead controls
- ST, limit-state, and newly listed stock filtering are not yet fully explicit in the production path

That combination of evidence and caveats makes the project more credible than a pure headline-return backtest, while still leaving room for further audit work.

## Current Strengths

The project currently demonstrates:

- a clear economic identity as a dynamic mean-reversion framework
- explicit integration of exposure control and entry/exit logic
- modular implementation that is easier to review than a monolithic script
- preserved raw trading records and holdings data
- strong attribution and diagnostics support
- a formalized stability-test archive across many key assumptions

## Current Limitations

Several limitations still remain:

- the project still depends on JoinQuant-specific APIs and platform behavior
- the fixed stock-pool assumption should continue to be stress-tested and documented
- some robustness experiments still need better summary tables rather than raw folder-only storage
- the strategy remains implementation-sensitive, especially under high turnover and cost pressure

## Recommended Reading Order

If the goal is to understand the project efficiently:

1. `README.md`
2. `REPRODUCIBILITY.md`
3. `Code/Complete_code.py`
4. `Code/modular_dmr_mfa/`
5. `Backtest-Raw-Results/Performance_Summary.csv`
6. `Attribution Analysis/`
7. `Stability/`

## Conclusion

`DMR-MFA` is best viewed as a structured active-trading research system rather than only a rebound script.

Its strongest value lies in combining:

- dynamic regime-based exposure control
- rebound-focused stock selection
- capital-flow confirmation
- technical exit refinement
- and now a clearer archive of robustness validation

That makes the strategy far more credible than a single high-return backtest snapshot.
