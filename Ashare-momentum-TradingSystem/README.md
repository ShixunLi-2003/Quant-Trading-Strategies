# A-Share Short-Horizon Momentum Research System

[Cantonese version](README.yue.md)

An end-to-end research repository for short-horizon A-share ranking, minute-level execution simulation, and ETF-based regime control. The project documents the full research decision trail: data alignment, factor diagnostics, model comparison, cost-aware simulation, out-of-sample validation, risk overlays, and execution safeguards.

## At a Glance

- **Research question:** can daily and intraday market structure identify a robust three-session cross-sectional ranking signal after realistic A-share trading costs?
- **Selected design:** a 60% defensive low-volatility component and 40% broad momentum component, up to three holdings, minute-level execution, and adaptive ETF exposure.
- **Evidence status:** stronger than the selected market benchmarks in the observed sample, but not yet sufficient to claim persistent or institutionally validated alpha.

![Research workflow](results/figures/research_workflow.png)

## Headline Results

| Experiment | Actual usable period | Total return | Maximum drawdown | Interpretation |
|---|---:|---:|---:|---|
| Strict tuned candidate | 2025-07-02 to 2026-09-08 | 28.87% | -17.75% | Includes 30 bps adverse slippage on each side, commission, and stamp duty |
| Locked-parameter holdout | 2026-04-01 to 2026-09-08 | 6.09% | -20.77% | Positive holdout result, but risk remains material |
| 14:53 minute execution | 2025-12-25 to 2026-09-08 | 29.86% | -9.81% | 57 usable periods and 98.41% exact-time execution |
| Adaptive ETF continuous OOS | 2025-12-25 to 2026-09-08 | 34.10% | -8.02% | Exposure selected without using the current test period |
| No ETF overlay, same OOS sequence | 2025-12-25 to 2026-09-08 | 20.03% | -18.31% | Direct control for the ETF overlay |

These figures are research simulations, not audited live performance.

## Core Evidence

### 1. Factor Direction and Statistical Stability

The original broad momentum score is weak in this sample. The defensive component is the more reliable signal: it favors lower late-session returns, realized volatility, daily amplitude, and VWAP distance while retaining early-session strength. The selected blend preserves this defensive effect without discarding all momentum information.

![Composite factor robustness](results/figures/factor_ic_robustness.png)

- Defensive score: full-sample mean Rank IC `0.0474`, Newey-West `t=3.59`.
- Selected 60/40 blend: full-sample mean IC `0.0316`, `t=2.71`.
- Selected blend in the locked holdout: mean IC `0.0551`, `t=2.43`.

The preferred quantile diagnostic uses three non-overlapping calendar sleeves so that three-session labels are not compounded as if they were independent daily positions.

![Non-overlapping factor quantiles](results/figures/factor_nonoverlap_quantiles.png)

All three holdout sleeves have positive Q5-Q1 spreads and monotonicity of `0.9`, `0.9`, and `1.0`. Individual spread t-statistics remain between `1.16` and `1.52`, reflecting the limited 36–37 observations per sleeve.

### 2. Strict Portfolio Performance and Rolling Stability

The strict simulator applies finite capital, 100-share board lots, minimum commission, stamp duty, price filters, and 30 bps adverse slippage on both entry and exit.

![Strict backtest equity curves](results/figures/strict_backtest_equity_curves.png)

![Twenty-period rolling returns](results/figures/rolling_window_returns.png)

The selected strategy is positive in `71.8%` of 78 rolling windows. Median 20-period return is `7.25%`; the worst window is `-16.60%`. The result is materially better than the baseline, but it is not uniformly profitable across regimes.

### 3. Minute-Level Execution

The execution study tests a narrow range of scheduled exit times rather than selecting freely from every minute. The adopted time is 14:53, which balances implementation time and observed return without relying on the final minutes of the session.

![Exit-time sensitivity](results/figures/exit_time_sensitivity.png)

![14:53 minute execution equity](results/figures/scheduled_1453_equity_curve.png)

Minute bars improve price realism but cannot reproduce queue priority, partial fills, cancellations, or intrabar price paths.

### 4. ETF Regime Overlay and Market Benchmarks

ETF breadth is computed after session `t` and becomes effective for the next session. Nested rolling selection chooses among pre-declared breadth, confirmation, scope, and exposure candidates.

![ETF overlay comparison](results/figures/etf_overlay_oos_comparison.png)

![Adaptive ETF continuous OOS equity](results/figures/etf_overlay_continuous_oos_equity.png)

Over the actual common interval, the adaptive strategy returned `34.10%`, while five broad and growth ETF benchmarks returned between `-3.07%` and `17.76%`. The strategy also had a smaller drawdown than every selected benchmark.

![Matched-period benchmark comparison](results/figures/matched_period_benchmark_comparison.png)

This establishes matched-sample outperformance only. It is not a long-run alpha regression and does not eliminate benchmark-selection or regime-selection risk.

### 5. Model Selection Includes Negative Results

Ridge regression, random forest, and multilayer perceptron models were evaluated with embargoed walk-forward predictions. All three underperformed in the locked holdout, so the simpler fixed blend was retained.

![Model holdout comparison](results/figures/model_holdout_comparison.png)

Keeping unsuccessful model families in the repository makes the selection path auditable and avoids presenting only favorable experiments.

## Reproducibility

| Scope | Repository support | Requirement |
|---|---|---|
| Install package and run tests | Fully reproducible | Python 3.10 or 3.11 |
| Rebuild all published figures | Fully reproducible | Included aggregate result tables |
| Rebuild factors, IC, and quantiles | Reproducible with data | Standardized daily and one-minute market tables |
| Rebuild walk-forward model predictions | Reproducible with data | Generated factor panel |
| Run the generic cost-aware portfolio simulator | Reproducible with data | Candidate table containing scores and entry/exit prices |
| Rebuild the exact headline experiments | Not reproducible from this repository alone | Licensed raw market history and original dated research inputs |
| Run live broker execution | Intentionally excluded | Private credentials, account state, and vendor runtime |

Quick verification:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest
python scripts/generate_report_assets.py
```

Factor research with licensed data:

```bash
python scripts/run_factor_research.py \
  --daily data/raw/daily.parquet \
  --minute data/raw/minute.parquet \
  --output results/reproduced \
  --horizon 3 \
  --low-volatility-weight 0.6
```

The required schemas and exact reproduction boundary are documented in [Data Contract](docs/DATA_CONTRACT.md) and [Reproducibility](docs/REPRODUCIBILITY.md).

## Repository Layout

```text
configs/                 Public research parameters
docs/                    Methodology, data contract, quality assessment, and limitations
results/figures/          Publication-ready evidence shown in this README
results/tables/           Aggregate outputs, robustness tables, and decision records
scripts/                  Reproduction and report-generation entry points
src/ashare_momentum/      Reusable data, factor, model, risk, backtest, and execution modules
tests/                    Point-in-time, ownership, and statistical-validation tests
```

The root README intentionally shows only the decision-critical charts. The remaining sensitivity tables and archived comparisons are indexed in [Research Results](results/README.md).

## Research Controls

- Signal timestamps precede execution timestamps.
- Three-session labels use a matching training embargo and HAC-adjusted inference.
- ETF exposure for a session is derived only from information available before that session.
- Backtests include board lots, minimum commission, stamp duty, and adverse slippage.
- Live ownership logic caps sells at strategy-managed quantity and protects pre-existing inventory.
- Public files exclude account identifiers, credentials, live orders, positions, machine paths, and broker logs.

## Interpretation

This is a strong research-engineering and portfolio project with moderate statistical strategy evidence. The largest remaining constraints are the 57-period minute/OOS sample, six nested ETF folds, and missing historical point-in-time universe snapshots in several archived experiments. A durable-alpha claim would require longer untouched forward results and complete dated universe history.

See [Methodology](docs/METHODOLOGY.md), [Research Quality Assessment](docs/RESEARCH_QUALITY.md), and [Limitations](docs/LIMITATIONS.md) for the full technical record.
