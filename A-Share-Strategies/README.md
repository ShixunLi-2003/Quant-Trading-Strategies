# A-Share Strategy Research Repository

This directory contains the A-share portion of the broader cross-asset research portfolio. The focus is on two flagship strategy systems and one supplementary archive:

- `1.A-Share Cross-Factor Alpha Research & Live Execution System`
- `2.A-Share Dynamic Mean Reversion & Multi-Factor Flow Alpha (DMR-MFA)`
- `3.A-Share Oversold-Rebound-Timing-Strategy`

The first two are the primary interview-facing projects. Together they show breadth across two different A-share alpha paradigms:

- medium-frequency multi-factor stock selection
- higher-elasticity mean-reversion and active trading

## Flagship Projects

### 1. A-Share Cross-Factor Alpha Research & Live Execution System

This project combines:

- technical factors such as momentum, volatility, volume ratio, RSI, and breakout
- fundamental factors such as rolling PE, expected growth, gross margin, debt ratio, and market cap
- industry and region overlays
- adaptive rebalance and risk-control logic
- QMT signal-forwarding awareness in the workflow design

It is the clearest example in this directory of an institutional-style equity alpha research system.

### 2. A-Share Dynamic Mean Reversion & Multi-Factor Flow Alpha (DMR-MFA)

This project centers on:

- benchmark Bollinger-band regime detection
- dynamic holding-capacity adjustment
- oversold rebound entry logic
- positive main-capital-flow confirmation
- OBV and BBI-based exit refinement

It is best viewed as a more aggressive active-trading framework rather than a traditional low-turnover stock-selection model.

### 3. A-Share Oversold-Rebound-Timing-Strategy

This folder remains part of the research archive and preserves additional idea development, factor work, and timing-layer experiments. Compared with the first two projects, it is less central to the current interview-facing narrative.

## Research Structure

Each mature strategy folder is organized around four layers:

1. `Code`
   Canonical implementation plus review-friendly modular components where available.
2. `Factor Analysis` or `Factor_Analysis`
   Signal research used to inspect predictive behavior, redundancy, and intuition.
3. `Backtest-Raw-Results` and `Result_Images`
   Performance artifacts, including both raw exports and presentation-friendly summaries.
4. `Attribution Analysis` and `Stability`
   Audit and robustness layers covering attribution, risk decomposition, transaction diagnostics, and sensitivity testing.

## Why These Projects Are More Than Backtest Tuning

The stronger claim for this directory is not that the strategies are proven beyond doubt, but that they are supported by a more serious evidence chain than a typical student backtest.

Evidence against pure overfitting includes:

- multiple regime windows are archived instead of only one favorable sample
- raw holdings, trade details, and daily exposure exports are preserved
- attribution outputs make it easier to inspect where returns are actually coming from
- `Stability` folders archive cost, threshold, universe, capacity, and parameter perturbations
- the two flagship projects follow different economic stories, which reduces the impression of one reusable hindsight recipe

Residual risks are stated openly:

- both flagship A-share systems still depend on JoinQuant-specific APIs
- some anti-lookahead controls should be rerun and summarized more explicitly
- some robustness families still need cleaner comparison summary tables

## Why The Stability Layer Matters

The addition of explicit `Stability` directories is one of the most important quality upgrades in this A-share package.

Each standardized test family preserves artifacts such as:

- `benefits_overview.png`
- `daily_holdings_and_exposure.csv`
- `daily_performance_comparison.csv`
- `trade_execution_details.csv`

This makes it easier to inspect:

- parameter sensitivity
- cost stress
- position-capacity sensitivity
- universe or stock-pool robustness
- rebalance and risk-control behavior

Strong reported performance raises the standard for robustness evidence. It does not lower it.

## Recommended Reading Order

If your goal is to review the A-share work efficiently:

1. read the project README of `1` and `2`
2. inspect `REPRODUCIBILITY.md`
3. inspect `Code/Complete_code.py`
4. inspect the modular package if present
5. inspect `Backtest-Raw-Results/Performance_Summary.csv`
6. inspect `Attribution Analysis`
7. inspect `Stability`

## Current Strengths

- the flagship projects are structured as research systems rather than isolated scripts
- multiple market-regime slices are preserved
- raw trade and holdings exports are retained
- attribution and style diagnostics are included
- robustness work is formalized into dedicated folders
- the implementation layer already shows modular engineering intent

## Current Limitations

- the repository still depends on JoinQuant-specific APIs and environment assumptions
- not every strategy folder has the same documentation maturity
- most stability folders preserve raw test outputs but not yet unified comparison summaries
- some experiment context is still expressed through folder naming rather than explicit metadata

## Conclusion

The A-share portion of this repository is meant to show breadth across both stock-selection and active-trading research. Its strongest value lies in preserving the full chain:

`factor idea -> implementation -> backtest -> attribution -> stability validation`

That full chain is what makes the work interview-relevant.
