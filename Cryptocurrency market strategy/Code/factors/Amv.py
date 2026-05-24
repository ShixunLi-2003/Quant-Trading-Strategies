"""Compute a normalized AMV-style price-volume factor."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Scale rolling average transaction price within its recent range."""
    factor_name = args[0]
    amount_moving = candle_df["volume"] * (candle_df["open"] + candle_df["close"]) / 2
    amv = amount_moving.rolling(param).sum() / candle_df["volume"].rolling(param).sum()
    amv_min = amv.rolling(param).min()
    amv_max = amv.rolling(param).max()
    candle_df[factor_name] = (amv - amv_min) / (amv_max - amv_min)
    return candle_df
