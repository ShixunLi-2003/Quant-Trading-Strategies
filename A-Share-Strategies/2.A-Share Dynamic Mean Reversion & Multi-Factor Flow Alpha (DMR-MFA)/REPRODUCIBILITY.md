# Reproducibility Guide

This document explains how to reproduce the backtests archived in this folder for `A-Share Dynamic Mean Reversion & Multi-Factor Flow Alpha (DMR-MFA)`.

## 1. Canonical Implementation

The canonical workflow for this strategy is:

- [Code/Complete_code.py](./Code/Complete_code.py) as the JoinQuant entry script
- `Code/modular_dmr_mfa/` as the internal logic package actually called by that entry script

Unlike the first strategy in this repository, the modular package here is directly wired into the top-level JoinQuant script, so the archived results should map closely to the modular implementation.

## 2. Platform and Data Source

This strategy was built for the JoinQuant backtest environment and depends on `jqdata` / JoinQuant APIs.

The implementation uses the following JoinQuant interfaces:

- `run_daily`, `set_benchmark`, `set_option`, `set_slippage`, `set_order_cost`
- `get_current_data` for pause status and latest prices
- `attribute_history` for benchmark and stock-level daily time series
- `get_money_flow` for main-capital flow filtering
- `order_target_value` for target-value execution

In practical terms, the strategy combines:

- benchmark data from CSI 300 history
- stock-level daily close and volume history
- JoinQuant money-flow data for `net_amount_main`
- live portfolio state from JoinQuant's runtime context

## 3. Fixed Backtest Configuration

The following settings are explicitly defined in `Code/modular_dmr_mfa/strategy_orchestrator.py` and `strategy_config.py`:

- Benchmark: `000300.XSHG`
- Real-price mode: `set_option("use_real_price", True)`
- Slippage: `FixedSlippage(0.002)`
- Order cost:
  - `open_tax=0.0`
  - `close_tax=0.001`
  - `open_commission=0.0003`
  - `close_commission=0.0003`
  - `min_commission=5.0`
- Asset type: `stock`

The strategy is scheduled with:

- `before_open`: `before_market_open`
- `open`: `market_open`
- `11:25`: `check_stop_loss_take_profit`
- `14:50`: `check_stop_loss_take_profit`

Important note:

- The backtest date range is selected in JoinQuant's backtest panel rather than in code.
- To recreate the archived outputs, use the windows shown in `Backtest-Raw-Results/`, such as `2011-2026`, `2014-2015`, `2018`, `2022-2024`, and `2024-2026`.

## 4. Stock Pool Definition

This strategy uses a fixed stock pool rather than a dynamic universe.

The current hard-coded stock pool in `Code/modular_dmr_mfa/strategy_config.py` is:

```text
601117.XSHG, 601600.XSHG, 601888.XSHG, 300274.XSHE, 300750.XSHE,
601919.XSHG, 002049.XSHE, 603881.XSHG, 002335.XSHE, 600089.XSHG,
002236.XSHE, 002056.XSHE, 300866.XSHE, 002611.XSHE, 600760.XSHG,
300693.XSHE, 002402.XSHE, 002600.XSHE, 300207.XSHE, 603486.XSHG,
000591.XSHE, 000027.XSHE, 600011.XSHG, 601899.XSHG, 603799.XSHG,
002340.XSHE, 002780.XSHE, 600160.XSHG, 601225.XSHG, 002555.XSHE,
600803.XSHG, 300059.XSHE, 002736.XSHE
```

### Eligibility logic inside the fixed pool

The current implementation keeps a stock as a candidate only if:

- it is not paused according to `get_current_data()`
- its most recent `get_money_flow(..., count=1, end_date=context.current_dt)` record exists
- the latest `net_amount_main` is positive
- the latest close is below the close from `10` trading days earlier
- the `3`-day return is less than `-7%`

### Filters that are not explicitly implemented

The current version does not explicitly screen out:

- ST / PT stocks
- limit-up or limit-down trading states
- newly listed stocks

That should be stated clearly in interviews and in future robustness work.

### Future-data risk statement

This strategy explicitly sets `use_real_price=True`, but it does not explicitly call `set_option('avoid_future_data', True)`.

For a strict audit workflow, reproduce the archived results first, then rerun a control version with future-data protection enabled and compare the drift.

## 5. Factor and Parameter Definitions

### 5.1 Benchmark regime factor

The benchmark regime is determined from CSI 300 Bollinger-band position:

- benchmark: `000300.XSHG`
- lookback: `20` days
- band width: `2.0` standard deviations
- if benchmark close is above upper band:
  - regime = `up`
  - target holding count = `7`
- if benchmark close is below lower band:
  - regime = `down`
  - target holding count = `3`
- otherwise:
  - regime = `neutral`
  - target holding count = `5`

### 5.2 Entry factors

### Ten-day downtrend

- lookback: `10` days
- condition: current close is lower than the close `10` trading days ago

### Three-day sharp drawdown

- lookback: `3` days
- formula: `(close[t] - close[t-3]) / close[t-3]`
- threshold: less than `-7%`

### Main capital flow filter

- source: `get_money_flow`
- field used: `net_amount_main`
- condition: latest `net_amount_main > 0`

Candidate ranking rule:

- qualifying stocks are sorted by `3`-day drawdown magnitude
- more negative short-term drawdowns rank higher

### 5.3 Exit factors and hard thresholds

### Hard take-profit

- liquidate when position return is greater than or equal to `+15%`

### Hard stop-loss

- liquidate when position return is less than or equal to `-3.5%`

### OBV divergence exit

- only evaluated when floating profit is above `+1%`
- uses `10` days of `close` and `volume`
- triggers when OBV reaches a short-term high but price does not confirm

### BBI slope exit

- only evaluated when floating return is below or equal to `-3%`
- uses daily `close` history
- triggers when the BBI composite average is sloping downward

### 5.4 Execution style

- positions are managed in target-value form through `order_target_value`
- when holdings exceed target capacity, the weakest profit-rate names are pruned first
- when capacity is below target, available cash is deployed equally across new qualifying candidates

## 6. Step-by-Step Reproduction Workflow

1. Create a JoinQuant strategy project.
2. Copy `Code/Complete_code.py` into the JoinQuant editor.
3. Ensure the supporting modular files under `Code/modular_dmr_mfa/` are mirrored into the JoinQuant project structure or merged into a single-file variant for platform execution.
4. In the JoinQuant backtest panel, choose one of the archived windows shown under `Backtest-Raw-Results/`.
5. Keep benchmark, slippage, and commission settings aligned with the code.
6. Run the backtest and export summary metrics, holdings, and trade records.
7. Compare the outputs with the CSV files already stored in this repository.

If you want a minimum-faithfulness reproduction, prioritize these checks:

- holding-count transitions should move between `3`, `5`, and `7`
- entry names should come from the fixed pool only
- buys should require both oversold structure and positive `net_amount_main`
- exits should primarily come from the four documented exit rules

## 7. Expected Output Artifacts

Successful reproduction should generate artifacts structurally similar to:

- `Backtest-Raw-Results/Performance_Summary.csv`
- per-window `strategy_summary_metrics.csv`
- per-window `daily_holdings_and_exposure.csv`
- per-window `trade_execution_details.csv`
- attribution outputs under `Attribution Analysis/`
- headline charts under `Result_Images/`

Small deviations can happen if:

- JoinQuant has revised historical money-flow or price data
- the rerun backtest end date differs from the archived run
- platform default settings differ from the original run
- anti-lookahead settings are changed in the control rerun

## 8. Known Limitations

- This project is reproducible inside JoinQuant, not as a fully detached local Python backtester.
- The stock pool is manually fixed in code, so pool selection itself should be treated as a research assumption.
- The current implementation does not explicitly filter ST, limit-up, limit-down, or newly listed names.
- The repository does not yet contain a frozen environment file or a local mock data adapter for JoinQuant APIs.
- The exact archived date boundaries are implied by folder naming, not hard-coded in the strategy.

## 9. Official JoinQuant Documentation

The following official pages are the most relevant references for reproducing this project:

- JoinQuant API overview: [https://www.joinquant.com/help/api/help?name=api](https://www.joinquant.com/help/api/help?name=api)
- JoinQuant stock data documentation: [https://www.joinquant.com/help/data/stock](https://www.joinquant.com/help/data/stock)
- JoinQuant index data documentation: [https://www.joinquant.com/help/data/index](https://www.joinquant.com/help/data/index)
- JoinQuant community note on avoiding future data: [https://www.joinquant.com/community/post/detailMobile?postId=36720](https://www.joinquant.com/community/post/detailMobile?postId=36720)
