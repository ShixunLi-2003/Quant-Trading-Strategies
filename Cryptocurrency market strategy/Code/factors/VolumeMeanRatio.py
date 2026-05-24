"""Compare short-horizon and long-horizon average volume."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Measure whether recent volume is expanding relative to a longer baseline."""
    factor_name = args[0]
    short_mean = candle_df["volume"].rolling(param, min_periods=1).mean()
    long_mean = candle_df["volume"].rolling(2 * param, min_periods=1).mean()
    candle_df[factor_name] = short_mean / long_mean
    return candle_df
