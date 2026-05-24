"""Aggregate target weights through time and run the execution simulator."""

from __future__ import annotations

import time

import pandas as pd

from config import backtest_name, backtest_path, is_pure_long
from core.equity import calc_equity
from core.model.backtest_config import BacktestConfig, load_config
from core.utils.path_kit import get_file_path

pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)


def simulate_performance(conf: BacktestConfig, select_results: pd.DataFrame, show_plot: bool = True):
    """Convert selection output into time-series exposures and simulate portfolio returns."""
    start = time.time()
    print("Aggregating portfolio weights...")
    df_ratio = agg_target_alloc_ratio(conf, select_results)
    print(f"Weight aggregation finished in {time.time() - start:.3f}s")

    if conf.is_day_period:
        print(f"Simulating {len(df_ratio):,} daily revaluation points...")
    else:
        print(f"Simulating {len(df_ratio):,} hourly revaluation points ({len(df_ratio) / 24:,.0f} days)...")

    pivot_dict = pd.read_pickle(get_file_path("data", "market_pivot.pkl"))
    if is_pure_long:
        df_spot_ratio = df_ratio
        df_swap_ratio = pd.DataFrame(0, index=df_ratio.index, columns=df_ratio.columns)
        pivot_dict_spot = pivot_dict
        pivot_dict_swap = pivot_dict
    else:
        df_spot_ratio = pd.DataFrame(0, index=df_ratio.index, columns=df_ratio.columns)
        df_swap_ratio = df_ratio
        pivot_dict_spot = pivot_dict
        pivot_dict_swap = pivot_dict

    calc_equity(conf, pivot_dict_spot, pivot_dict_swap, df_spot_ratio, df_swap_ratio, show_plot=show_plot)
    print(f"Backtest finished in {time.time() - start:.3f}s")
    return conf.report


def agg_target_alloc_ratio(conf: BacktestConfig, df_select: pd.DataFrame):
    """Pivot target allocations into a timestamp-by-symbol exposure matrix."""
    start_date = df_select["candle_begin_time"].min()
    end_date = df_select["candle_begin_time"].max()
    candle_begin_times = pd.date_range(start_date, end_date, freq=conf.hold_period_type, inclusive="both")

    df_ratio = df_select.pivot_table(
        index="candle_begin_time",
        columns="symbol",
        values="target_alloc_ratio",
        aggfunc="sum",
    )
    df_ratio = df_ratio.reindex(candle_begin_times, fill_value=0)
    return df_ratio.rolling(conf.strategy.hold_period, min_periods=1).sum()


if __name__ == "__main__":
    backtest_config = load_config()
    results = pd.read_pickle(get_file_path(backtest_path, backtest_name, "select_result.pkl"))
    simulate_performance(backtest_config, results)
