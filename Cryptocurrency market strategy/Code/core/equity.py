"""Convert target allocations into executed portfolio paths and summary reports."""

from __future__ import annotations

import time

import numba as nb
import numpy as np
import pandas as pd

from core.evaluate import strategy_evaluate
from core.figure import draw_equity_curve_plotly
from core.model.backtest_config import BacktestConfig
from core.rebalance import RebAlways
from core.simulator import Simulator
from core.utils.functions import load_min_qty
from core.utils.path_kit import get_file_path
from update_min_qty import min_qty_path

pd.set_option("display.max_rows", 1000)
pd.set_option("expand_frame_repr", False)


def calc_equity(
    conf: BacktestConfig,
    pivot_dict_spot: dict,
    pivot_dict_swap: dict,
    df_spot_ratio: pd.DataFrame,
    df_swap_ratio: pd.DataFrame,
    show_plot: bool = True,
) -> None:
    """Run the execution simulator and write portfolio diagnostics to disk."""
    if len(df_spot_ratio) != len(df_swap_ratio) or not df_swap_ratio.index.equals(df_spot_ratio.index):
        raise RuntimeError("Spot and swap target weight matrices are misaligned.")

    candle_begin_times = df_spot_ratio.index.to_series().reset_index(drop=True)
    spot_symbols = sorted(df_spot_ratio.columns)
    swap_symbols = sorted(df_swap_ratio.columns)

    pivot_dict_spot = align_pivot_dimensions(pivot_dict_spot, spot_symbols, candle_begin_times)
    pivot_dict_swap = align_pivot_dimensions(pivot_dict_swap, swap_symbols, candle_begin_times)

    spot_lot_sizes = read_lot_sizes(min_qty_path / "min_qty_spot.csv", spot_symbols)
    swap_lot_sizes = read_lot_sizes(min_qty_path / "min_qty_swap.csv", swap_symbols)
    pos_calc = RebAlways(spot_lot_sizes.to_numpy(), swap_lot_sizes.to_numpy())

    start = time.perf_counter()
    equities, turnovers, fees, funding_fees, margin_rates = start_simulation(
        init_capital=conf.initial_usdt,
        leverage=conf.leverage,
        spot_lot_sizes=spot_lot_sizes.to_numpy(),
        swap_lot_sizes=swap_lot_sizes.to_numpy(),
        spot_c_rate=conf.spot_c_rate,
        swap_c_rate=conf.swap_c_rate,
        spot_min_order_limit=float(conf.spot_min_order_limit),
        swap_min_order_limit=float(conf.swap_min_order_limit),
        min_margin_rate=conf.margin_rate,
        spot_ratio=df_spot_ratio[spot_symbols].to_numpy(),
        swap_ratio=df_swap_ratio[swap_symbols].to_numpy(),
        spot_open_p=pivot_dict_spot["open"].to_numpy(),
        spot_close_p=pivot_dict_spot["close"].to_numpy(),
        spot_vwap1m_p=pivot_dict_spot["vwap1m"].to_numpy(),
        swap_open_p=pivot_dict_swap["open"].to_numpy(),
        swap_close_p=pivot_dict_swap["close"].to_numpy(),
        swap_vwap1m_p=pivot_dict_swap["vwap1m"].to_numpy(),
        funding_rates=pivot_dict_swap["funding_rate"].to_numpy(),
        pos_calc=pos_calc,
    )
    print(f"Simulation finished in {time.perf_counter() - start:.3f}s")

    account_df = pd.DataFrame(
        {
            "candle_begin_time": candle_begin_times,
            "equity": equities,
            "turnover": turnovers,
            "fee": fees,
            "funding_fee": funding_fees,
            "margin_ratio": margin_rates,
        }
    )
    account_df["nav"] = account_df["equity"] / conf.initial_usdt
    account_df["return"] = account_df["nav"].pct_change().fillna(0)
    account_df["liquidated"] = np.where(account_df["margin_ratio"] < conf.margin_rate, 1, np.nan)
    account_df["liquidated"] = account_df["liquidated"].ffill().fillna(0).astype(int)

    result_folder = conf.get_result_folder()
    account_df.to_csv(result_folder / "equity_curve.csv", encoding="utf-8-sig", index=False)

    metrics, year_return, month_return, quarter_return = strategy_evaluate(account_df, net_col="nav", pct_col="return")
    conf.set_report(metrics)
    metrics.to_csv(result_folder / "strategy_metrics.csv", encoding="utf-8-sig")
    year_return.to_csv(result_folder / "yearly_returns.csv", encoding="utf-8-sig")
    quarter_return.to_csv(result_folder / "quarterly_returns.csv", encoding="utf-8-sig")
    month_return.to_csv(result_folder / "monthly_returns.csv", encoding="utf-8-sig")

    if show_plot:
        benchmark_dict = pd.read_pickle(get_file_path("data", "candle_data_dict.pkl"))
        for benchmark in ("BTC-USDT", "ETH-USDT"):
            if benchmark not in benchmark_dict:
                continue
            benchmark_df = benchmark_dict[benchmark][["candle_begin_time", "close"]].rename(columns={"close": benchmark})
            account_df = account_df.merge(benchmark_df, on="candle_begin_time", how="left")
            account_df[benchmark] = account_df[benchmark].ffill()
            benchmark_return_col = f"{benchmark}_return"
            benchmark_nav_col = f"{benchmark}_nav"
            account_df[benchmark_return_col] = account_df[benchmark].pct_change().fillna(0)
            account_df[benchmark_nav_col] = (1 + account_df[benchmark_return_col]).cumprod()
            del account_df[benchmark], account_df[benchmark_return_col]

        print(metrics)
        print(f"Total fees: {account_df['fee'].sum():,.2f} USDT")

        data_dict = {"Strategy NAV": "nav"}
        if "BTC-USDT_nav" in account_df.columns:
            data_dict["BTC NAV"] = "BTC-USDT_nav"
        if "ETH-USDT_nav" in account_df.columns:
            data_dict["ETH NAV"] = "ETH-USDT_nav"

        title = (
            f"NAV={metrics.at['cumulative_nav', 'value']}, "
            f"Annual={metrics.at['annual_return', 'value']}, "
            f"MDD={metrics.at['max_drawdown', 'value']}"
        )
        draw_equity_curve_plotly(
            account_df,
            data_dict=data_dict,
            date_col="candle_begin_time",
            right_axis={"Drawdown": "drawdown"},
            title=title,
            desc=conf.get_fullname(),
            path=result_folder / "equity_curve.html",
        )


def read_lot_sizes(path, symbols):
    """Map symbols to their minimum trade sizes."""
    default_min_qty, min_qty_dict = load_min_qty(path)
    lot_sizes = 0.1 ** pd.Series(min_qty_dict)
    return lot_sizes.reindex(symbols, fill_value=0.1 ** default_min_qty)


def align_pivot_dimensions(market_pivot_dict, symbols, candle_begin_times):
    """Slice each pivot matrix to the same timestamp and symbol index."""
    return {name: df.loc[candle_begin_times, symbols] for name, df in market_pivot_dict.items()}


@nb.jit(nopython=True, boundscheck=True)
def start_simulation(
    init_capital,
    leverage,
    spot_lot_sizes,
    swap_lot_sizes,
    spot_c_rate,
    swap_c_rate,
    spot_min_order_limit,
    swap_min_order_limit,
    min_margin_rate,
    spot_ratio,
    swap_ratio,
    spot_open_p,
    spot_close_p,
    spot_vwap1m_p,
    swap_open_p,
    swap_close_p,
    swap_vwap1m_p,
    funding_rates,
    pos_calc,
):
    """Simulate execution, financing, and PnL across all bars."""
    n_bars = spot_ratio.shape[0]
    n_syms_spot = spot_ratio.shape[1]
    n_syms_swap = swap_ratio.shape[1]

    start_lots_spot = np.zeros(n_syms_spot, dtype=np.int64)
    start_lots_swap = np.zeros(n_syms_swap, dtype=np.int64)
    funding_rates_spot = np.zeros(n_syms_spot, dtype=np.float64)

    turnovers = np.zeros(n_bars, dtype=np.float64)
    fees = np.zeros(n_bars, dtype=np.float64)
    equities = np.zeros(n_bars, dtype=np.float64)
    funding_fees = np.zeros(n_bars, dtype=np.float64)
    margin_rates = np.zeros(n_bars, dtype=np.float64)

    sim_spot = Simulator(init_capital, spot_lot_sizes, spot_c_rate, start_lots_spot, spot_min_order_limit)
    sim_swap = Simulator(0, swap_lot_sizes, swap_c_rate, start_lots_swap, swap_min_order_limit)

    for i in range(n_bars):
        equity_spot, _, pos_value_spot = sim_spot.on_open(spot_open_p[i], funding_rates_spot, spot_open_p[i])
        equity_swap, funding_fee, pos_value_swap = sim_swap.on_open(swap_open_p[i], funding_rates[i], swap_open_p[i])

        position_val = np.sum(np.abs(pos_value_spot)) + np.sum(np.abs(pos_value_swap))
        margin_rate = 10000.0 if position_val < 1e-8 else (equity_spot + equity_swap) / float(position_val)

        if margin_rate < min_margin_rate:
            margin_rates[i] = margin_rate
            break

        equity_spot, turnover_spot, fee_spot = sim_spot.on_execution(spot_vwap1m_p[i])
        equity_swap, turnover_swap, fee_swap = sim_swap.on_execution(swap_vwap1m_p[i])

        equity_spot_close = sim_spot.on_close(spot_close_p[i])
        equity_swap_close = sim_swap.on_close(swap_close_p[i])

        funding_fees[i] = funding_fee
        equities[i] = equity_spot + equity_swap
        turnovers[i] = turnover_spot + turnover_swap
        fees[i] = fee_spot + fee_swap
        margin_rates[i] = margin_rate

        equity_leveraged = (equity_spot_close + equity_swap_close) * leverage
        target_lots_spot, target_lots_swap = pos_calc.calc_lots(
            equity_leveraged,
            spot_close_p[i],
            sim_spot.lots,
            spot_ratio[i],
            swap_close_p[i],
            sim_swap.lots,
            swap_ratio[i],
        )
        sim_spot.set_target_lots(target_lots_spot)
        sim_swap.set_target_lots(target_lots_swap)

    return equities, turnovers, fees, funding_fees, margin_rates
