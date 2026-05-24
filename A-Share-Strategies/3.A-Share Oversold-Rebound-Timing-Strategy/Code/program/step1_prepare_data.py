"""Prepare daily stock data and cache aligned market panels for later stages."""

import time
import warnings
from concurrent.futures.process import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from config import n_jobs
from core.market_essentials import cal_fuquan_price, cal_zdt_price, merge_with_index_data
from core.model.backtest_config import BacktestConfig, load_config
from core.utils.path_kit import get_file_path

warnings.filterwarnings("ignore")
pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)

STOCK_DATA_COLS = [
    "stock_code",
    "stock_name",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "prev_close",
    "volume",
    "turnover",
    "float_market_cap",
    "total_market_cap",
]


def prepare_data(conf: BacktestConfig) -> None:
    """Load raw daily equity files, align them to the trading calendar, and cache the result."""
    start_time = time.time()

    stock_code_list = []
    for filename in conf.stock_data_path.glob("*.csv"):
        if filename.stem.startswith("."):
            continue
        if filename.stem.startswith("bj") and "bj" in conf.excluded_boards:
            continue
        if filename.stem.startswith("sh68") and "kcb" in conf.excluded_boards:
            continue
        if filename.stem.startswith("sz30") and "cyb" in conf.excluded_boards:
            continue
        stock_code_list.append(filename.stem)
    stock_code_list = sorted(stock_code_list)

    index_data = conf.read_index_with_trading_date()
    all_candle_data_dict: dict[str, pd.DataFrame] = {}

    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        futures = []
        for code in stock_code_list:
            file_path = conf.stock_data_path / f"{code}.csv"
            futures.append(executor.submit(pre_process, file_path, index_data))

        for future in tqdm(futures, desc="Prepare daily stock data", total=len(futures)):
            df = future.result()
            if not df.empty:
                code = df["stock_code"].iloc[0]
                all_candle_data_dict[code] = df

    pd.to_pickle(
        all_candle_data_dict,
        get_file_path("data", "runtime_cache", "stock_preprocessed_data.pkl"),
    )
    pd.to_pickle(
        make_market_pivot(all_candle_data_dict),
        get_file_path("data", "runtime_cache", "full_market_price_pivot.pkl"),
    )


def pre_process(stock_file_path: str | Path, index_data: pd.DataFrame) -> pd.DataFrame:
    """Prepare one stock's daily history and merge it with the master trading calendar."""
    df = pd.read_csv(
        stock_file_path,
        encoding="gbk",
        skiprows=1,
        parse_dates=["trade_date"],
        usecols=STOCK_DATA_COLS,
    )

    pct_change = df["close"] / df["prev_close"] - 1
    turnover_rate = df["turnover"] / df["float_market_cap"]
    trading_days = df.index.astype(int) + 1
    average_price = df["turnover"] / df["volume"]

    df = df.assign(
        **{
            "return": pct_change,
            "turnover_rate": turnover_rate,
            "listed_trading_days": trading_days,
            "average_price": average_price,
        }
    )
    df = cal_fuquan_price(df, fuquan_type="backward_adjusted")
    df = cal_zdt_price(df)
    df = merge_with_index_data(df, index_data.copy(), fill_0_list=["turnover_rate"])

    if df.empty:
        return pd.DataFrame(columns=STOCK_DATA_COLS)

    df = df.assign(
        **{
            "next_day_tradable": df["is_tradable"].astype("int8").shift(-1),
            "next_day_open_limit_up": df["open_limit_up"].astype("int8").shift(-1),
            "next_day_st": df["stock_name"].str.contains("ST", na=False).astype("int8").shift(-1),
            "next_day_delisted": df["stock_name"]
            .str.contains("Delisted", na=False)
            .astype("int8")
            .shift(-1),
        }
    )
    state_cols = [
        "next_day_tradable",
        "next_day_st",
        "next_day_delisted",
    ]
    df[state_cols] = df[state_cols].ffill()
    return df


def make_market_pivot(market_dict: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Build open, close, and prev-close pivot tables for the simulator."""
    cols = ["trade_date", "stock_code", "open", "close", "prev_close"]
    df_list = [df[cols].dropna(subset=["stock_code"]) for df in market_dict.values()]
    df_all_market = pd.concat(df_list, ignore_index=True)
    return {
        "open": df_all_market.pivot(values="open", index="trade_date", columns="stock_code"),
        "close": df_all_market.pivot(values="close", index="trade_date", columns="stock_code"),
        "preclose": df_all_market.pivot(values="prev_close", index="trade_date", columns="stock_code"),
    }


if __name__ == "__main__":
    backtest_config = load_config()
    prepare_data(backtest_config)
