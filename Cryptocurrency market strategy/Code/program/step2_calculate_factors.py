"""Compute all configured factor columns and cache the research matrix."""

from __future__ import annotations

import time

import pandas as pd
from tqdm import tqdm

from core.model.backtest_config import BacktestConfig, load_config
from core.utils.factor_hub import FactorHub
from core.utils.path_kit import get_file_path

pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)

FACTOR_KLINE_COL_LIST = ["candle_begin_time", "symbol", "is_trading"]


def calc_factors(conf: BacktestConfig) -> None:
    """Load prepared candles, compute factor columns, and cache a merged factor table."""
    print("Calculating factors...")
    start = time.time()

    candle_df_list = pd.read_pickle(get_file_path("data", "cache", "all_candle_df_list.pkl"))
    all_factor_df_list = []

    for candle_df in tqdm(candle_df_list, desc="factor pass", total=len(candle_df_list)):
        if conf.is_day_period:
            candle_df = trans_period_for_day(candle_df)

        candle_df = candle_df.dropna(subset=["symbol"]).reset_index(drop=True)
        factor_df = calc_factors_by_candle(candle_df, conf)
        all_factor_df_list.append(factor_df)

    all_factors_df = pd.concat(all_factor_df_list, ignore_index=True)
    all_factors_df["symbol"] = pd.Categorical(all_factors_df["symbol"])
    all_factors_df.sort_values(by=["candle_begin_time", "symbol"]).reset_index(drop=True).to_pickle(
        get_file_path("data", "cache", "all_factors_df.pkl")
    )

    print(f"Factor calculation finished in {time.time() - start:.2f}s")


def trans_period_for_day(df: pd.DataFrame, date_col: str = "candle_begin_time") -> pd.DataFrame:
    """Resample hourly bars into daily bars for daily-holding strategies."""
    df = df.set_index(date_col)
    agg_dict = {
        "symbol": "first",
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "quote_volume": "sum",
        "trade_num": "sum",
        "taker_buy_base_asset_volume": "sum",
        "taker_buy_quote_asset_volume": "sum",
        "funding_rate": "sum",
        "first_candle_time": "first",
        "is_trading": "last",
    }
    return df.resample("1D").agg(agg_dict).reset_index()


def calc_factors_by_candle(candle_df: pd.DataFrame, conf: BacktestConfig) -> pd.DataFrame:
    """Compute all factor columns required by the active strategy for one symbol."""
    factor_series_dict = {}
    for factor_name, param_list in conf.factor_params_dict.items():
        factor = FactorHub.get_by_name(factor_name)
        work_df = candle_df.copy()
        for param in param_list:
            factor_col_name = f"{factor_name}_{param}"
            work_df = factor.signal(work_df, param, factor_col_name)
            factor_series_dict[factor_col_name] = work_df[factor_col_name]

    result = pd.DataFrame(
        {
            "candle_begin_time": candle_df["candle_begin_time"],
            "symbol": candle_df["symbol"],
            "close": candle_df["close"],
            "next_close": candle_df["close"].shift(-1),
            **factor_series_dict,
            "is_trading": candle_df["is_trading"],
        }
    ).sort_values(by="candle_begin_time")

    first_candle_time = candle_df.iloc[0]["first_candle_time"] + pd.to_timedelta(f"{conf.min_kline_num}h")
    result = result[result["candle_begin_time"] >= first_candle_time]

    if result["candle_begin_time"].max() < pd.to_datetime(conf.end_date):
        next_hold_time = result["candle_begin_time"] + pd.Timedelta(conf.hold_period)
        missing_next = result[result.loc[next_hold_time.index, "next_close"].isna()]["candle_begin_time"]
        if not missing_next.empty:
            result = result[result["candle_begin_time"] <= missing_next.min() - pd.Timedelta(conf.hold_period)]

    result = result[
        (result["candle_begin_time"] >= pd.to_datetime(conf.start_date))
        & (result["candle_begin_time"] < pd.to_datetime(conf.end_date))
    ]
    return result


if __name__ == "__main__":
    calc_factors(load_config())
