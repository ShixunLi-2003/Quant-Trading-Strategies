"""Prepare market data and cache pivot tables used by the backtest engine."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from config import black_list, is_pure_long, spot_path, start_date, swap_path
from core.utils.functions import is_trade_symbol
from core.utils.path_kit import get_file_path

pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.width", 100)


def prepare_data():
    """Load raw hourly candles, normalize missing bars, and cache research inputs."""
    print("Preparing market data...")
    start = time.time()

    data_path = spot_path if is_pure_long else swap_path
    symbol_list = sorted(
        file_path.stem
        for file_path in data_path.rglob("*-USDT.csv")
        if is_trade_symbol(file_path.stem)
    )
    print(f"Detected {len(symbol_list):,} tradeable symbols")

    candle_data_dict = {}
    for symbol in symbol_list:
        path = data_path / f"{symbol}.csv"
        print(f"[preprocess] {symbol}\t{path}")
        candle_data_dict[symbol] = preprocess_kline(path)

    pd.to_pickle(candle_data_dict, get_file_path("data", "candle_data_dict.pkl"))

    all_candle_df_list = [candle_df for symbol, candle_df in candle_data_dict.items() if symbol not in black_list]
    pd.to_pickle(all_candle_df_list, get_file_path("data", "cache", "all_candle_df_list.pkl"))

    market_pivot = make_market_pivot(candle_data_dict)
    pd.to_pickle(market_pivot, get_file_path("data", "market_pivot.pkl"))

    print(f"Data preparation finished in {time.time() - start:.2f}s")
    return all_candle_df_list, market_pivot


def preprocess_kline(filename) -> pd.DataFrame:
    """Standardize one symbol's raw candle file into a gap-filled research dataset."""
    df = pd.read_csv(filename, encoding="gbk", parse_dates=["candle_begin_time"], skiprows=1)
    df = df.drop_duplicates(subset=["candle_begin_time"], keep="last")

    is_swap = "fundingRate" in df.columns
    first_candle_time = df["candle_begin_time"].min()
    last_candle_time = df["candle_begin_time"].max()

    hourly_range = pd.DataFrame({"candle_begin_time": pd.date_range(first_candle_time, last_candle_time, freq="1h")})
    df = hourly_range.merge(df, on="candle_begin_time", how="left", sort=True)
    df = df.sort_values("candle_begin_time").drop_duplicates(subset=["candle_begin_time"], keep="last")

    df["close"] = df["close"].ffill()
    df["open"] = df["open"].fillna(df["close"])

    candle_data_dict = {
        "candle_begin_time": df["candle_begin_time"],
        "symbol": pd.Categorical(df["symbol"].ffill()),
        "open": df["open"],
        "high": df["high"].fillna(df["close"]),
        "low": df["low"].fillna(df["close"]),
        "close": df["close"],
        "volume": df["volume"].fillna(0),
        "quote_volume": df["quote_volume"].fillna(0),
        "trade_num": df["trade_num"].fillna(0),
        "taker_buy_base_asset_volume": df["taker_buy_base_asset_volume"].fillna(0),
        "taker_buy_quote_asset_volume": df["taker_buy_quote_asset_volume"].fillna(0),
        "funding_rate": df["fundingRate"].fillna(0) if is_swap else 0,
        "avg_price_1m": df["avg_price_1m"].fillna(df["open"]),
        "avg_price_5m": df["avg_price_5m"].fillna(df["open"]),
        "is_trading": np.where(df["volume"] > 0, 1, 0).astype(np.int8),
        "first_candle_time": pd.Series([first_candle_time] * len(df)),
        "last_candle_time": pd.Series([last_candle_time] * len(df)),
    }
    return pd.DataFrame(candle_data_dict)


def make_market_pivot(market_dict):
    """Create timestamp-symbol matrices for open, close, execution, and funding inputs."""
    cols = ["candle_begin_time", "symbol", "open", "close", "funding_rate", "avg_price_1m"]
    df_list = []
    for df in market_dict.values():
        df2 = df.loc[df["candle_begin_time"] >= pd.to_datetime(start_date), cols].dropna(subset="symbol")
        df_list.append(df2)

    df_all_market = pd.concat(df_list, ignore_index=True)
    df_all_market["symbol"] = pd.Categorical(df_all_market["symbol"])

    df_open = df_all_market.pivot(values="open", index="candle_begin_time", columns="symbol")
    df_close = df_all_market.pivot(values="close", index="candle_begin_time", columns="symbol")
    df_vwap1m = df_all_market.pivot(values="avg_price_1m", index="candle_begin_time", columns="symbol")
    df_rate = df_all_market.pivot(values="funding_rate", index="candle_begin_time", columns="symbol").fillna(0)

    return {"open": df_open, "close": df_close, "funding_rate": df_rate, "vwap1m": df_vwap1m}


if __name__ == "__main__":
    prepare_data()
