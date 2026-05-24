"""Implement an RSJ-style directional asymmetry factor."""

from __future__ import annotations

import numpy as np


def signal(candle_df, param, *args):
    """Measure asymmetry between positive and negative returns scaled by range efficiency."""
    factor_name = args[0]
    if isinstance(param, (tuple, list)) and len(param) >= 2:
        lookback, _ = param[:2]
    else:
        lookback = 20

    ret = candle_df["close"].pct_change()
    ret_pos = ret.where(ret > 0, 0)
    ret_neg = ret.where(ret < 0, 0).abs()
    sum_up = ret_pos.rolling(lookback, min_periods=1).sum()
    sum_down = ret_neg.rolling(lookback, min_periods=1).sum()
    sum_abs = ret.abs().rolling(lookback, min_periods=1).sum()

    rsj = (sum_up - sum_down) / sum_abs.replace(0, np.nan)
    rsj = rsj.fillna(0)

    high_max = candle_df["high"].rolling(lookback, min_periods=1).max()
    low_min = candle_df["low"].rolling(lookback, min_periods=1).min()
    price_range = (high_max - low_min).replace(0, np.nan)
    efficiency = (sum_abs / price_range).fillna(0)

    candle_df[factor_name] = efficiency * rsj
    return candle_df
