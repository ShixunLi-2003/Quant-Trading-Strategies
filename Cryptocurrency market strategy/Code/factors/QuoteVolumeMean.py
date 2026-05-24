"""Measure rolling quote-volume intensity."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Smooth quote turnover over a rolling window."""
    factor_name = args[0]
    candle_df[factor_name] = candle_df["quote_volume"].rolling(param, min_periods=1).mean()
    return candle_df
