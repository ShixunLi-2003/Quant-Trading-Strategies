"""Implement a price-volume correlation decay factor inspired by Alpha#22."""

from __future__ import annotations


def signal(candle_df, param, *args):
    """Combine decaying price-volume correlation with local price volatility."""
    factor_name = args[0] if args else "W22"
    if isinstance(param, (tuple, list)) and len(param) >= 3:
        corr_window, delta_window, std_window = param[:3]
    else:
        corr_window, delta_window, std_window = 5, 5, 20

    rolling_corr = candle_df["high"].rolling(window=corr_window, min_periods=1).corr(candle_df["quote_volume"]).fillna(0)
    delta_corr = rolling_corr - rolling_corr.shift(delta_window).fillna(0)
    close_std = candle_df["close"].rolling(window=std_window, min_periods=1).std().fillna(0)
    candle_df[factor_name] = -delta_corr * close_std
    return candle_df
