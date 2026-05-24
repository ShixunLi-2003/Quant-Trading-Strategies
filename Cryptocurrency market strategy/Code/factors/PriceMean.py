"""Compute a rolling average traded price factor."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Smooth average traded price over a rolling window."""
    factor_name = args[0]
    quote_volume = candle_df["quote_volume"].rolling(param, min_periods=1).mean()
    volume = candle_df["volume"].rolling(param, min_periods=1).mean()
    candle_df[factor_name] = quote_volume / volume
    return candle_df
