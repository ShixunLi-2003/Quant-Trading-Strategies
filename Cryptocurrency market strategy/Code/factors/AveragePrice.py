"""Compute the contemporaneous traded average price."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Estimate average traded price from quote turnover and base volume."""
    factor_name = args[0]
    candle_df[factor_name] = candle_df["quote_volume"] / candle_df["volume"]
    return candle_df
