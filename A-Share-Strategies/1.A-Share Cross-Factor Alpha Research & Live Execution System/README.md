# A-Share Cross-Factor Alpha Research & Live Execution System

## Project Overview

This project is an A-share multi-factor equity strategy research system that combines factor design, stock selection, portfolio construction, JoinQuant backtesting, attribution analysis, stability validation, and live-execution signal forwarding.

The strategy blends technical, fundamental, and industry-overlay information into a medium-frequency stock-selection framework with explicit risk-control and execution-awareness layers.

The repository is organized to preserve the full research workflow rather than only the final backtest script.

## Interview Snapshot

### Key Results

- `2011-2026`: annualized return `35.36%`, Sharpe `1.586`, max drawdown `14.54%`
- `2018` bear market window: strategy `9.26%` versus benchmark `-25.31%`
- `2022-2024` sideways/down window: strategy `16.14%` versus benchmark `-21.77%`
- return profile is steadier and more defensive than the higher-elasticity A-share trading strategy in this repository

### Why It's Credible

- combines technical, fundamental, and overlay blocks instead of relying on one tuned signal
- preserves multi-window results, raw holdings, trade execution details, attribution outputs, and stability tests
- uses a time-varying benchmark constituent universe rather than a hindsight-fixed stock list
- includes explicit sensitivity work around cost, rebalance cadence, stock count, and universe choice

### Main Risks

- still depends on JoinQuant APIs and platform behavior
- anti-lookahead controls should be rerun and summarized more explicitly
- overlay logic is economically intuitive, but can still benefit from cleaner ablation evidence

## Strategy Architecture

The strategy is built around five main layers:

### 1. Technical factor block

The technical block evaluates signals such as:

- price momentum
- realized volatility
- volume ratio
- RSI
- breakout strength

These factors are intended to capture trend persistence, participation intensity, and short-term price structure quality.

### 2. Fundamental factor block

The fundamental block evaluates signals such as:

- rolling or TTM PE
- expected growth
- net profit growth
- gross margin quality
- debt ratio
- market capitalization

These factors are intended to balance valuation, growth, balance-sheet quality, and business strength.

### 3. Industry and region overlay

The strategy includes an overlay layer that:

- scores preferred industry groups
- avoids weak or structurally unattractive industry groups
- applies regime-aware sector preference adjustments
- adds limited region-based bonus logic
- performs industry boom checks via index or futures proxies

This layer is not the core signal source, but it helps shape the final portfolio profile.

### 4. Portfolio construction and regime adjustment

The strategy dynamically adjusts:

- benchmark-regime interpretation
- technical versus fundamental weighting
- rebalance frequency
- target holding count
- position sizing and rebalance thresholds

This makes the system more adaptive than a static weighted ranker.

### 5. Risk control and execution

The risk layer includes:

- tiered stop-loss logic
- tiered take-profit logic
- portfolio drawdown reduction logic
- rise filters and profit-deterioration filters
- execution-aware target-order generation
- QMT signal forwarding in the integrated workflow

## Repository Structure

```text
1.A-Share Cross-Factor Alpha Research & Live Execution System/
|- Code/
|- Factor_Analysis/
|- Backtest-Raw-Results/
|- Attribution analysis/
|- Result_Images/
|- Stability/
|- REPRODUCIBILITY.md
`- README.md
```

### `Code`

The implementation layer.

- `Complete_code.py`
  The canonical JoinQuant-style monolithic implementation for reproduction and testing.
- `modular_alpha/`
  A refactored version of the strategy logic organized into configuration, factor, filter, overlay, portfolio, and risk-control modules.

### `Factor_Analysis`

The signal research layer, containing single-factor and diagnostic notebooks used to inspect the behavior of technical and fundamental features before final aggregation.

### `Backtest-Raw-Results`

The archived raw export layer, containing:

- performance summary tables
- daily holdings and exposure data
- trade execution detail exports
- multi-period backtest windows

### `Attribution analysis`

The audit layer for:

- return decomposition
- style exposure
- industry exposure
- Brinson-style attribution
- drawdown analysis
- trading diagnostics
- slippage impact visualization

### `Result_Images`

The presentation layer for quick visual inspection of headline backtest outcomes across major periods.

### `Stability`

The robustness-validation layer.

This directory now stores a structured archive of parameter and stress-test runs. Each subfolder follows a standardized naming convention and contains:

- `benefits_overview.png`
- `daily_holdings_and_exposure.csv`
- `daily_performance_comparison.csv`
- `trade_execution_details.csv`

## Backtest Profile

## Final Performance Summary

The archived final backtest summary from `Backtest-Raw-Results/Performance_Summary.csv` is shown below.

| Backtest Period | Strategy Annualized Return | Benchmark Return (CSI 300) | Alpha | Beta | Sharpe Ratio | Sortino Ratio | Information Ratio | Max Drawdown | Profit/Loss Ratio | Winning Rate | Strategy Volatility |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2011-2026 (Long Term) | 35.36% | 50.90% | 0.319 | 0.488 | 1.586 | 2.547 | 1.622 | 14.54% | 2.092 | 0.477 | 0.198 |
| 2014-2015 (Bull/Volatile) | 66.85% | 60.13% | 0.524 | 0.451 | 2.540 | 3.951 | 1.492 | 12.57% | 2.580 | 0.486 | 0.247 |
| 2018 (Bear Market) | 9.26% | -25.31% | 0.167 | 0.384 | 0.323 | 0.440 | 1.830 | 14.26% | 1.404 | 0.460 | 0.162 |
| 2022-2024 (Sideways/Down) | 16.14% | -21.77% | 0.197 | 0.500 | 0.703 | 1.240 | 1.574 | 13.54% | 1.571 | 0.442 | 0.173 |
| 2024-2026 (Recent) | 24.43% | 39.00% | 0.139 | 0.549 | 1.091 | 1.687 | 0.478 | 11.23% | 1.769 | 0.464 | 0.187 |

## Key Takeaways

- The strategy shows its strongest overall profile in long-horizon and mixed-regime settings rather than in one isolated market phase.
- Defensive behavior is a meaningful part of the edge: the strategy stays positive in weak periods such as `2018` and `2022-2024`, while benchmark performance is materially negative.
- Drawdown control is relatively disciplined for a concentrated active A-share stock-selection framework, with max drawdown staying in a comparatively moderate range across archived windows.
- The main practical risk is not obvious regime collapse, but sensitivity to implementation details such as rebalance cadence, cost assumptions, and concentration settings.

According to the archived long-horizon and regime-sliced results, the strategy shows:

- strong long-term absolute return generation
- meaningful resilience in weak-market environments
- moderate beta versus the broad market
- acceptable drawdown control relative to return
- nontrivial dependence on implementation details such as rebalance cadence and cost assumptions

The full-period and regime-sliced results suggest that the strategy is not just a single-regime winner. It retains positive absolute return in weak-market environments, while also keeping drawdowns relatively contained compared with many concentrated A-share stock-selection systems.

That last point is exactly why the `Stability` directory matters.

## Stability and Robustness Coverage

The current `Stability` directory already includes a meaningful first-generation robustness suite.

The archived tests cover areas such as:

- benchmark regime-window sensitivity
- rebalance-frequency sensitivity
- stock-count sensitivity
- maximum-position sensitivity
- slippage stress
- commission stress
- universe substitution
- portfolio drawdown reduction sensitivity

Representative folder names now include:

- `benchmark_regime_window_20_to_15_2011_2026`
- `benchmark_regime_window_20_to_30_2011_2026`
- `rebalance_schedule_10_10_15_to_5_10_20_2011_2026`
- `rebalance_schedule_10_10_15_to_10_15_20_2011_2026`
- `stock_count_5_to_3_2011_2026`
- `stock_count_5_to_7_2011_2026`
- `stock_count_5_to_10_2011_2026`
- `max_position_per_stock_0_20_to_0_15_2011_2026`
- `max_position_per_stock_0_20_to_0_25_2011_2026`
- `slippage_0_002_to_0_003_2011_2026`
- `slippage_0_002_to_0_005_2011_2026`
- `slippage_0_002_to_0_01_2011_2026`
- `commission_0_0003_to_0_00045_2011_2026`
- `universe_hs300_to_zz500_2011_2026`

This is already enough to support a serious discussion of whether the strategy is:

- overly sensitive to benchmark regime definitions
- overly dependent on specific rebalance timing
- too concentrated
- too fragile under more realistic transaction costs
- too dependent on a single stock universe

## Why the Stability Layer Matters

This strategy reports attractive performance characteristics. When a strategy looks strong, the main research question shifts from:

`Can it backtest well?`

to:

`Does it remain economically coherent when assumptions are perturbed?`

The `Stability` folder is therefore not a cosmetic appendix. It is a core part of the evidence base for the project.

## Why This Is More Than Curve Fitting

This project does not claim immunity from overfitting. The more defensible claim is that the current evidence base is stronger than a single tuned backtest.

Evidence that pushes the project beyond naive curve fitting includes:

- the primary universe is time-varying through `get_index_stocks(...)` rather than a hindsight-fixed stock list
- performance is archived across long-term, bull, bear, sideways, and recent windows instead of one favorable regime only
- the repository preserves raw holdings, trade execution details, and attribution outputs, making the return path auditable
- the `Stability` directory perturbs cost, rebalance cadence, stock count, maximum position, and universe assumptions
- the strategy combines technical, fundamental, and overlay layers, which can be challenged separately instead of hidden inside one opaque score

The honest caveat is that some additional audit work would still strengthen the anti-overfitting case:

- rerunning with stricter anti-lookahead settings should be summarized explicitly
- overlay and ablation studies can still be made more formal
- JoinQuant data and platform assumptions remain part of the research environment

## Current Strengths

The project currently demonstrates:

- integration of technical and fundamental alpha blocks
- awareness of portfolio construction under changing market states
- explicit defensive logic at both position and portfolio level
- preserved raw results and trade records
- meaningful attribution coverage
- a growing archive of systematic robustness tests

## Current Limitations

Several limitations still remain:

- the project is still tied to JoinQuant APIs and environment assumptions
- some experiments are archived as raw folders rather than with comparison summary tables
- the overlay layer is economically intuitive but could still be further validated through more explicit ablation work
- formal out-of-sample protocol writeups could be stronger

## Recommended Reading Order

If you want to review the project efficiently:

1. `README.md`
2. `REPRODUCIBILITY.md`
3. `Code/Complete_code.py`
4. `Code/modular_alpha/`
5. `Backtest-Raw-Results/Performance_Summary.csv`
6. `Attribution analysis/`
7. `Stability/`

## Conclusion

This project is best understood as a complete A-share cross-factor research system, not just a backtest script.

Its strongest value lies in combining:

- multi-block signal design
- explicit portfolio-control logic
- reproducible backtest artifacts
- attribution evidence
- and now a more formalized stability-testing archive

That combination makes the project substantially more credible than a single impressive performance chart.
