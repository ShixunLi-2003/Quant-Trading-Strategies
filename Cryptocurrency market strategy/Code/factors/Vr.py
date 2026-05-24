"""Compute a rolling volume-ratio indicator."""

from __future__ import annotations

import numpy as np


def signal(candle_df, param, *args):
    """Compare up-volume against down-volume over a rolling window."""
    factor_name = args[0]
    prev_close = candle_df["close"].shift(1)
    candle_df["av"] = np.where(candle_df["close"] > prev_close, candle_df["volume"], 0)
    candle_df["bv"] = np.where(candle_df["close"] < prev_close, candle_df["volume"], 0)
    candle_df["cv"] = np.where(candle_df["close"] == prev_close, candle_df["volume"], 0)

    avs = candle_df["av"].rolling(param, min_periods=1).sum()
    bvs = candle_df["bv"].rolling(param, min_periods=1).sum()
    cvs = candle_df["cv"].rolling(param, min_periods=1).sum()
    candle_df[factor_name] = (avs + 0.5 * cvs) / (bvs + 0.5 * cvs)
    return candle_df
