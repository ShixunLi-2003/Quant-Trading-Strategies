# Reproducibility

## Scope

This package is a portable English presentation layer around the current production configuration of the oversold rebound timing strategy. After moving the folder out of the original workspace, only three raw input roots need to be remapped in `Code/configuration.py`:

- `stock_data_path`
- `index_data_path`
- `fin_data_path`

No packaged `.pkl` cache is required as an input. Runtime caches are generated automatically from the raw datasets listed below.

## Execution Invariants

- Strategy name: `Oversold Rebound Timing Strategy`
- Holding period: `5D`
- Selection count: `10`
- Active timing overlay: `Volume Expansion Moving Average Timing (40, 0.6, 15)`
- Excluded boards: Beijing Stock Exchange (`bj`)
- Listing-age threshold: `250` trading days

## Required Daily A-Share Price Table

The packaged code expects the following stock-level daily fields after any vendor-specific renaming step:

| Alias | Type | Required | Used In | Description |
| --- | --- | --- | --- | --- |
| `stock_code` | string | Yes | All stages | Exchange-prefixed security identifier such as `sh600000` or `sz000001`. |
| `stock_name` | string | Yes | Filtering, diagnostics | Security name used for ST and delisting filters. |
| `trade_date` | date | Yes | All stages | Trading-day key for all joins, rankings, and simulations. |
| `open` | float | Yes | Simulation, limit rules | Daily open price. |
| `high` | float | Yes | Limit rules, adjusted-price build | Daily high price. |
| `low` | float | Yes | Limit rules, adjusted-price build | Daily low price. |
| `close` | float | Yes | Factors, adjusted-price build, simulation | Daily close price. |
| `prev_close` | float | Yes | Daily return, limit rules | Previous close used for daily returns and price-limit calculations. |
| `volume` | float | Yes | Long-term low-volume factor, average price | Daily traded share volume. |
| `turnover` | float | Yes | Volume-contraction factor, turnover factors, flow proxy | Daily traded amount in CNY. |
| `float_market_cap` | float | Yes | Turnover factors | Daily float market capitalization. |
| `total_market_cap` | float | Yes | Rolling PE, holding diagnostics | Daily total market capitalization. |

## Derived Daily Fields Built by the Package

The package derives these internally from the raw price table, so they do not need to exist in the source file:

- `return`
- `turnover_rate`
- `listed_trading_days`
- `average_price`
- `adj_factor`
- `adjusted_open`
- `adjusted_high`
- `adjusted_low`
- `adjusted_close`
- `limit_up_price`
- `limit_down_price`
- `limit_up_locked`
- `limit_down_locked`
- `open_limit_up`
- `open_limit_down`
- `next_day_tradable`
- `next_day_open_limit_up`
- `next_day_st`
- `next_day_delisted`

## Required Financial Data Table

The active package needs one financial field because the current filter stack includes `Rolling PE`.

| Alias | Type | Required | Used In | Description |
| --- | --- | --- | --- | --- |
| `stock_code` | string | Yes | Finance-file partitioning | Security identifier matching the daily price table. |
| `publish_date` | date | Yes | As-of merge | Announcement date used to align financial reports with market data. |
| `report_date` | date | Yes | TTM construction | Report-end date used to reconstruct quarter sequencing. |
| `R_np@xbx` | float | Yes | `rolling_pe.py` | Net profit field used to construct 4-quarter trailing net profit (`net_profit_ttm`). |

`rolling_pe.py` calculates `rolling_pe_none = total_market_cap / net_profit_ttm` and masks observations with non-positive trailing profit.

## Required Index Data Files

The strategy uses multiple benchmark/index files for different roles:

| File | Required Fields | Role |
| --- | --- | --- |
| `sh000001.csv` | `candle_end_time`, `open`, `close` | Trading-calendar backbone and benchmark return series for calendar construction. |
| `sh000300.csv` | `candle_end_time`, `open`, `close` | CSI 300 overlay in performance charts. |
| `sh000905.csv` | `candle_end_time`, `open`, `close` | CSI 500 overlay in performance charts. |
| `sh000852.csv` | `candle_end_time`, `close`, `amount` | Benchmark turnover-expansion input for the active timing overlay. |

## Strategy-Specific Factor Inputs

| Factor | Package Column | Raw Inputs Required |
| --- | --- | --- |
| Volume Contraction Factor `(15, 80)` | `volume_contraction_factor_15_80` | `turnover` |
| Turnover Rate `(15)` | `turnover_rate_15` | `turnover`, `float_market_cap` |
| Long-Term Low Volume `(30)` | `long_term_low_volume_30` | `volume` |
| Oversold `(39)` | `oversold_39` | `close` |
| Oversold `(270)` | `oversold_270` | `close` |
| Net Capital Inflow `(6)` | `net_capital_inflow_6` | `return`, `turnover` |
| Turnover Rate filter `(30)` | `turnover_rate_30` | `turnover`, `float_market_cap` |
| Rolling PE filter | `rolling_pe_none` | `total_market_cap`, `R_np@xbx` |

## Trading-Rule Assumptions Embedded in the Code

- ST names use a 5% limit.
- Main-board names use a 10% limit.
- STAR Market (`sh68`) and post-2020 ChiNext (`sz3`) use a 20% limit.
- Beijing board (`bj`) uses a 30% limit and is excluded by the current configuration.
- Suspended days are calendar-filled and marked through the generated `is_tradable` flag.

## Output Regeneration Sequence

After the raw data paths are updated, the package can be regenerated with the staged workflow under `Code`:

1. `backtest_main.py` for the full pipeline.
2. `program/step1_prepare_data.py` if only the raw market data changes.
3. `program/step2_calculate_factors.py` after changing factor definitions or factor parameters.
4. `program/step3_select_stocks.py` after changing only selection rules.
5. `program/step4_simulate_performance.py` after changing only execution or timing settings.

## Relocation Notes

- The packaged code is path-independent once the three raw-data roots in `Code/configuration.py` are repointed.
- The result, factor-analysis, attribution-analysis, and stability folders in this package preserve the source numeric outputs already exported from the original framework.
- Static `.png` figures in the package are regenerated directly from those source CSV outputs and do not introduce alternate backtest logic.
