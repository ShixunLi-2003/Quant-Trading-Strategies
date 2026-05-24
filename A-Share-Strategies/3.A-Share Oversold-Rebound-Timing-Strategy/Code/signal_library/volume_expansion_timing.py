"""Generate a timing signal from benchmark turnover expansion."""

from pathlib import Path

import numpy as np
import pandas as pd

from core.model.backtest_config import load_config


def equity_signal(equity_df: pd.DataFrame, *args) -> pd.Series:
    """Stay long when standardized benchmark turnover expands above a threshold."""
    lookback = int(args[0])
    threshold = float(args[1])

    conf = load_config()
    index_file = Path(conf.index_data_path) / "sh000852.csv"
    index_df = pd.read_csv(index_file, parse_dates=["candle_end_time"])
    index_df = index_df.rename(columns={"candle_end_time": "trade_date"})

    merged_df = equity_df.copy()
    merged_df["trade_date"] = pd.to_datetime(merged_df["trade_date"])
    merged_df = merged_df.merge(
        index_df[["trade_date", "close", "amount"]],
        on="trade_date",
        how="left",
    )
    merged_df["close"] = merged_df["close"].ffill()
    merged_df["amount"] = merged_df["amount"].ffill()

    merged_df["log_turnover"] = np.log(merged_df["amount"])
    merged_df["turnover_ma"] = merged_df["log_turnover"].rolling(lookback, min_periods=1).mean()
    merged_df["turnover_std"] = merged_df["log_turnover"].rolling(lookback, min_periods=1).std()
    merged_df["volume_expansion_score"] = (
        merged_df["log_turnover"] - merged_df["turnover_ma"]
    ) / merged_df["turnover_std"]

    signals = pd.Series(np.nan, index=merged_df.index)
    signals.loc[
        (merged_df["volume_expansion_score"] >= threshold)
        & (merged_df["volume_expansion_score"].shift(1) < threshold)
    ] = 1.0
    signals.loc[
        (merged_df["volume_expansion_score"] <= -threshold)
        & (merged_df["volume_expansion_score"].shift(1) > -threshold)
    ] = 0.0
    return signals.ffill().fillna(1.0)
