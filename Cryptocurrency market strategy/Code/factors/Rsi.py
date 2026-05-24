"""Compute a rolling RSI-style relative strength factor."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Measure the balance between recent positive and negative returns."""
    factor_name = args[0]
    pct = candle_df["close"].pct_change()
    up = pct.where(pct > 0, 0)
    down = pct.where(pct < 0, 0).abs()
    up_sum = up.rolling(param, min_periods=1).sum()
    down_sum = down.rolling(param, min_periods=1).sum()
    candle_df[factor_name] = up_sum / (up_sum + down_sum)
    return candle_df
