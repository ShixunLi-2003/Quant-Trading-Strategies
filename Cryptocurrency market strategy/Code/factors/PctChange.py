"""Measure n-period price momentum using close-to-close returns."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Compute close price percentage change over a fixed lookback."""
    factor_name = args[0]
    candle_df[factor_name] = candle_df["close"].pct_change(param)
    return candle_df
