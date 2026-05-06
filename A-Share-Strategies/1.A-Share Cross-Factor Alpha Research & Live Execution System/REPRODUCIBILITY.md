# Reproducibility Guide

This document explains how to reproduce the backtests archived in this folder for the `A-Share Cross-Factor Alpha Research & Live Execution System`.

## 1. Canonical Implementation

For reproduction purposes, treat [Code/Complete_code.py](./Code/Complete_code.py) as the canonical JoinQuant backtest entry script.

The `Code/modular_alpha/` package is a refactored review-friendly version of the same strategy logic, but the archived result folders in this project should be reproduced from the JoinQuant entry script workflow first.

## 2. Platform and Data Source

This strategy was built for the JoinQuant research/backtest environment and depends on `jqdata` / JoinQuant platform APIs.

The implementation uses the following JoinQuant data interfaces:

- `run_daily`, `set_benchmark`, `set_option`, `set_slippage`, `set_order_cost`
- `get_index_stocks` for the dynamic stock universe
- `get_current_data` for pause status and latest price
- `get_price` for daily OHLCV history and benchmark or sector-proxy history
- `get_industry` for industry classification
- `get_dominant_future` for mapped sector-futures proxy selection
- `get_security_info` for ST/PT screening and region-name inspection
- `get_fundamentals(query(...), date=...)` for valuation, income, forecast, and balance-sheet fields

In practical terms, the strategy combines:

- stock universe and benchmark data from JoinQuant index and market data APIs
- daily price and volume history from JoinQuant price history APIs
- industry classification metadata from JoinQuant industry APIs
- financial statement, valuation, and earnings forecast data from JoinQuant fundamentals APIs

## 3. Fixed Backtest Configuration

The following settings are explicitly defined in `set_backtest(context)` inside `Code/Complete_code.py`:

- Benchmark: `000300.XSHG`
- Real-price mode: `set_option('use_real_price', True)`
- Slippage: `FixedSlippage(0.002)`
- Order cost:
  - `open_tax=0`
  - `close_tax=0.001`
  - `open_commission=0.0003`
  - `close_commission=0.0003`
  - `min_commission=5`
- Asset type: `stock`

The strategy is scheduled with:

- `before_open`: `before_market_open`
- `09:30`: `market_open_rebalance`
- `11:25`: `market_open_stop_loss`
- `14:50`: `market_open_stop_loss`
- `after_close`: `after_market_close`

Important note:

- The backtest start date and end date are not hard-coded in the script. In JoinQuant, they are selected in the backtest panel.
- To reproduce the archived exports in this repository, use the date ranges indicated by the folders under `Backtest-Raw-Results/`, such as `2011-2026`, `2014-2015`, `2018`, `2022-2024`, and `2024-2026`.

## 4. Stock Universe Definition

The primary stock universe is:

- the constituents of `000300.XSHG`
- queried dynamically on each rebalance date through `get_index_stocks('000300.XSHG', date=context.current_dt)`

This means the stock pool is time-varying rather than fixed.

### Pre-trade eligibility filters

A stock is considered ineligible if any of the following is true:

- currently paused
- latest price is non-positive
- security display name contains `ST`, `*ST`, or `PT`
- 120-day cumulative rise is greater than or equal to `1.5`
- 720-day cumulative rise is greater than or equal to `4.0`
- trailing-twelve-month net profit growth is less than or equal to `-0.5`

### Industry boom filter

After ranking, the strategy applies an industry boom check:

- a stock's JoinQuant industry classification is mapped to a sector proxy
- some sectors use Shenwan-style industry index proxies such as `801750.XSHG`, `801080.XSHG`, `801730.XSHG`, `801150.XSHG`
- some cyclical sectors use dominant futures contracts such as `JM`, `MA`, `RB`, `CU`, `AL`, `SC`
- a stock passes the boom filter when the mapped proxy's `20`-day momentum is greater than or equal to `0`

### Future-data risk statement

This implementation does not explicitly call `set_option('avoid_future_data', True)`.

That does not by itself prove future-data leakage, but for strict audit purposes you should:

1. reproduce the archived results with the current code and settings
2. rerun a control backtest with `avoid_future_data=True`
3. compare whether any material performance drift appears

## 5. Factor and Parameter Definitions

### 5.1 Technical factors

The strategy computes the following technical scores from daily `close/high/low/volume` history:

- Momentum:
  - lookback: `20` trading days
  - formula: `close[t] / close[t-20] - 1`
  - weight: `8`
  - optimal range: `5%` to `15%`
- Volatility:
  - lookback: `20` trading days
  - computed from log returns
  - lower volatility is preferred
  - weight: `10`
  - optimal range in the code configuration: `10%` to `20%`
- Volume ratio:
  - short window: `5`
  - long window: `20`
  - formula: `MA(volume, 5) / MA(volume, 20)`
  - weight: `7`
  - optimal range: `1.0` to `1.5`
- RSI:
  - lookback: `14`
  - weight: `7`
  - optimal range: `40` to `60`
- Breakout:
  - lookback: `10`
  - formula: `(close[t] - max(high over prior window)) / prior_window_high`
  - threshold: `3%`
  - weight: `8`

### 5.2 Fundamental factors

The strategy computes the following fundamental scores:

- TTM PE:
  - TTM profit uses the latest `4` income records
  - market cap is taken from valuation data
  - weight: `12`
  - optimal range: `15` to `20`
  - soft upper cap in scoring: `30`
- Expected growth:
  - compares `forecast.forecast_net_profit` with trailing-twelve-month profit
  - weight: `10`
  - optimal range: `30%` to `100%`
  - minimum threshold: `5%`
- TTM net profit growth:
  - compares current TTM profit with prior-year TTM profit
  - weight: `10`
  - optimal range: `30%` to `100%`
  - minimum threshold: `5%`
- Gross margin:
  - computed as `(operating_revenue - operating_cost) / operating_revenue`
  - weight: `10`
  - optimal range: `30%` to `50%`
  - minimum threshold: `10%`
- Debt ratio:
  - computed as `total_liability / total_assets`
  - weight: `8`
  - optimal range: `20%` to `30%`
  - soft upper cap in scoring: `60%`
- Market capitalization:
  - weight: `10`
  - optimal range: `200` to `500`
  - acceptable range: `100` to `1000`

### 5.3 Regime adjustment and portfolio construction

- benchmark regime lookback: `20` days
- if benchmark return over the regime window is greater than `5%`:
  - market status: `bull`
  - technical multiplier: `1.2`
  - fundamental multiplier: `0.9`
  - rebalance interval: `10` days
- if benchmark return over the regime window is less than `-5%`:
  - market status: `bear`
  - technical multiplier: `0.8`
  - fundamental multiplier: `1.2`
  - rebalance interval: `15` days
- otherwise:
  - market status: `normal`
  - technical multiplier: `1.0`
  - fundamental multiplier: `1.0`
  - rebalance interval: `10` days

Portfolio construction rules:

- target holding count: `5`
- maximum position per stock: `20%` of portfolio equity
- board-lot normalization: `100` shares
- minimum rebalance buffer: roughly `10%` of one board-lot trade value
- in bear regime, the rebalance threshold is multiplied by `1.5`

### 5.4 Position-level and portfolio-level risk control

- stop-loss half reduction threshold: `-5%`
- stop-loss full liquidation threshold: `-7%`
- take-profit half reduction threshold: `+20%`
- take-profit full liquidation threshold: `+30%`
- portfolio drawdown threshold: `6%`
- portfolio drawdown trigger multiplier: `1.2`
- proportional portfolio reduction after trigger: `70%`

## 6. Step-by-Step Reproduction Workflow

### Option A: Reproduce archived backtests on JoinQuant

1. Create a JoinQuant strategy project.
2. Copy `Code/Complete_code.py` into the JoinQuant editor.
3. In the backtest panel, set the benchmark to `000300.XSHG` and choose one of the archived date windows.
4. Keep the cost and slippage settings consistent with the code.
5. Run the backtest.
6. Export the result tables and compare them with the corresponding files under `Backtest-Raw-Results/`.

### Option B: Review the refactored logic

1. Read `Code/modular_alpha/strategy_config.py` for the parameter layer.
2. Read `Code/modular_alpha/technical_factors.py` and `Code/modular_alpha/fundamental_factors.py` for the signal layer.
3. Read `Code/modular_alpha/portfolio_construction.py`, `stock_filters.py`, and `risk_controls.py` for the selection, order, and defense rules.
4. Cross-check the behavior against the JoinQuant entry script before treating the modular package as the exact production replica.

## 7. Expected Output Artifacts

If the reproduction succeeds, the outputs should be structurally similar to the artifacts already included in this folder:

- `Backtest-Raw-Results/Performance_Summary.csv`
- per-window `strategy_summary_metrics.csv`
- per-window `daily_holdings_and_exposure.csv`
- per-window `trade_execution_details.csv`
- attribution charts under `Attribution analysis/`
- headline result charts under `Result_Images/`

Exact values may differ slightly if:

- JoinQuant historical data revisions have occurred
- the backtest end date is not identical
- platform execution defaults have changed
- the local rerun uses stricter anti-lookahead settings

## 8. Known Limitations

- This project is reproducible within the JoinQuant environment, not as a standalone off-platform Python package.
- The code depends on JoinQuant-specific APIs and data schemas.
- The exact archived date boundaries are implied by folder naming, not hard-coded in the strategy.
- The repository does not yet include a frozen dependency file or a fully detached local data adapter.
- The monolithic JoinQuant script and the refactored modular package are conceptually aligned but not guaranteed to be byte-for-byte identical in every intermediate implementation detail, so archived-result reproduction should start from `Code/Complete_code.py`.
- The strategy includes a refactored modular implementation, but the monolithic JoinQuant script should remain the first reference for result reproduction.

## 9. Official JoinQuant Documentation

The following official pages are the most relevant references for reproducing this project:

- JoinQuant API overview: [https://www.joinquant.com/help/api/help?name=api](https://www.joinquant.com/help/api/help?name=api)
- JoinQuant stock data documentation: [https://www.joinquant.com/help/data/stock](https://www.joinquant.com/help/data/stock)
- JoinQuant index data documentation: [https://www.joinquant.com/help/data/index](https://www.joinquant.com/help/data/index)
- JoinQuant futures data documentation: [https://www.joinquant.com/help/data/futures](https://www.joinquant.com/help/data/futures)
- JoinQuant community note on avoiding future data: [https://www.joinquant.com/community/post/detailMobile?postId=36720](https://www.joinquant.com/community/post/detailMobile?postId=36720)
