"""
WorldQuant-Style Factors

Implements the adapted W-22, W-24, and W-42 factors used in the strategy research process.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def w_24(
    market_data: dict[str, pd.DataFrame],
    window_long: int = 100,
    window_short: int = 4,
    threshold: float = 0.15,
) -> pd.DataFrame:
    close = market_data["close"]
    ma_long = close.rolling(window_long, min_periods=window_long).mean()
    delta_ma_long = ma_long - ma_long.shift(window_long)
    close_lag = close.shift(window_long)
    condition = (delta_ma_long / close_lag) <= threshold

    min_close = close.rolling(window_long, min_periods=window_long).min()
    factor_a = -(close - min_close)
    factor_b = -(close - close.shift(window_short))
    return factor_a.where(condition, factor_b)


def w_22(
    market_data: dict[str, pd.DataFrame],
    corr_window: int = 4,
    delta_window: int = 3,
    std_window: int = 12,
) -> pd.DataFrame:
    high = market_data["high"]
    volume = market_data["volume"]
    close = market_data["close"]

    rolling_corr = high.rolling(corr_window).corr(volume)
    delta_corr = rolling_corr - rolling_corr.shift(delta_window)
    std_close = close.rolling(std_window).std()
    std_rank = std_close.rank(axis=1, pct=True, method="average")
    return -delta_corr * std_rank


def w_42(market_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    close = market_data["close"]
    amount = market_data["amount"]
    volume = market_data["volume"].replace(0, np.nan)
    vwap = amount / volume

    left = (vwap - close).rank(axis=1, pct=True, method="average")
    right = (vwap + close).rank(axis=1, pct=True, method="average")
    factor = left / right.replace(0, np.nan)
    return factor.replace([np.inf, -np.inf], np.nan)
