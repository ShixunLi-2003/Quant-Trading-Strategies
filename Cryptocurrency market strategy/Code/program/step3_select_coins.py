"""Filter the universe, rank assets cross-sectionally, and generate target weights."""

from __future__ import annotations

import time

import pandas as pd

from config import is_pure_long
from core.model.backtest_config import BacktestConfig, load_config
from core.utils.path_kit import get_file_path

pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)

FACTOR_KLINE_COL_LIST = ["candle_begin_time", "symbol", "is_trading"]


def select_coins(conf: BacktestConfig):
    """Turn factor values into long and short target allocations."""
    start = time.time()
    print("Selecting assets...")

    strategy = conf.strategy
    factor_df = pd.read_pickle(get_file_path("data", "cache", "all_factors_df.pkl"))
    factor_df = factor_df[(factor_df["is_trading"] == 1) & (~factor_df["symbol"].isin(conf.black_list))].copy()
    factor_df = factor_df.dropna(subset=strategy.factor_columns)
    factor_df = factor_df.dropna(subset=["symbol"]).sort_values(by=["candle_begin_time", "symbol"]).reset_index(drop=True)

    prev_cols = factor_df.columns
    result_df = strategy.calc_select_factor(factor_df)
    factor_df = factor_df[prev_cols].join(result_df[list(set(result_df.columns) - set(prev_cols))])

    long_df, short_df = strategy.filter_before_select(factor_df)
    if is_pure_long:
        short_df = pd.DataFrame(columns=short_df.columns)

    factor_df = select_long_and_short_coin(
        long_df,
        short_df,
        strategy.long_select_coin_num,
        strategy.short_select_coin_num,
        factor_name=strategy.factor_name,
    )

    if not is_pure_long:
        factor_df.loc[factor_df["side"] == 1, "target_alloc_ratio"] /= 2
        factor_df.loc[factor_df["side"] == -1, "target_alloc_ratio"] /= 2

    factor_df = factor_df[factor_df["target_alloc_ratio"].abs() > 1e-9]
    result_df = factor_df[[*FACTOR_KLINE_COL_LIST, "side", "target_alloc_ratio"]].copy()
    if result_df.empty:
        return result_df

    base_seconds = 3600 * 24 if strategy.is_day_period else 3600
    reference_date = pd.to_datetime("2017-01-01")
    time_diff_seconds = (result_df["candle_begin_time"] - reference_date).dt.total_seconds()
    offset = (time_diff_seconds / base_seconds).mod(strategy.period_num).astype("int8")
    result_df["offset"] = ((offset + 1 + strategy.period_num) % strategy.period_num).astype("int8")
    result_df = result_df[result_df["offset"].isin(strategy.offset_list)]
    if result_df.empty:
        return result_df

    select_result_df = result_df[[*FACTOR_KLINE_COL_LIST, "side", "offset", "target_alloc_ratio"]].copy()
    select_result_df["target_alloc_ratio"] = (
        select_result_df["target_alloc_ratio"] / len(strategy.offset_list) * select_result_df["side"]
    )

    select_result_df.to_pickle(conf.get_result_folder() / "select_result.pkl")
    print(f"Asset selection finished in {time.time() - start:.2f}s")
    return select_result_df


def select_long_and_short_coin(long_df, short_df, long_select_coin_num, short_select_coin_num, factor_name):
    """Select top-ranked longs and bottom-ranked shorts at each timestamp."""
    long_df = calc_select_factor_rank(long_df, factor_column=factor_name, ascending=True)
    if int(long_select_coin_num) == 0:
        long_df = long_df[long_df["universe_size"] * long_select_coin_num >= long_df["rank"]].copy()
    else:
        long_df = long_df[long_df["rank"] <= long_select_coin_num].copy()
    long_df["side"] = 1
    long_df["target_alloc_ratio"] = 1 / long_df.groupby("candle_begin_time")["symbol"].transform("size")

    if not is_pure_long:
        short_df = calc_select_factor_rank(short_df, factor_column=factor_name, ascending=False)
        if short_select_coin_num == "long_nums":
            long_select_num = long_df.groupby("candle_begin_time")["symbol"].size().rename("long_count").reset_index()
            short_df = short_df.merge(long_select_num, on="candle_begin_time", how="left")
            short_df = short_df[short_df["rank"] <= short_df["long_count"]].copy()
            del short_df["long_count"]
        elif int(short_select_coin_num) == 0:
            short_df = short_df[short_df["universe_size"] * short_select_coin_num >= short_df["rank"]].copy()
        else:
            short_df = short_df[short_df["rank"] <= short_select_coin_num].copy()

        short_df["side"] = -1
        short_df["target_alloc_ratio"] = 1 / short_df.groupby("candle_begin_time")["symbol"].transform("size")
        df = pd.concat([long_df, short_df], ignore_index=True)
    else:
        df = long_df

    df = df.sort_values(by=["candle_begin_time", "side"], ascending=[True, False]).reset_index(drop=True)
    del df["universe_size"], df["rank_max"]
    return df


def calc_select_factor_rank(df, factor_column: str = "composite_factor", ascending: bool = True):
    """Rank each asset within a timestamp-specific cross section."""
    df["rank"] = df.groupby("candle_begin_time")[factor_column].rank(method="min", ascending=ascending)
    df["rank_max"] = df.groupby("candle_begin_time")["rank"].transform("max")
    df = df.sort_values(by=["candle_begin_time", "rank"])
    df["universe_size"] = df.groupby("candle_begin_time")["symbol"].transform("size")
    return df


if __name__ == "__main__":
    select_coins(load_config())
