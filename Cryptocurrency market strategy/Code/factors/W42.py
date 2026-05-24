"""Implement a stabilized VWAP-versus-close dislocation factor."""

from __future__ import annotations

import numpy as np


def signal(candle_df, param, *args):
    """Normalize VWAP dislocation while clipping time-series outliers."""
    factor_name = args[0] if args else "W42"
    if isinstance(param, (tuple, list)) and len(param) >= 3:
        lower_quantile, upper_quantile, use_zscore = param[:3]
    else:
        lower_quantile, upper_quantile, use_zscore = 0.01, 0.99, True

    volume = candle_df["volume"].replace(0, np.nan)
    vwap = (candle_df["quote_volume"] / volume).replace([np.inf, -np.inf], np.nan)
    vwap = vwap.fillna(candle_df["close"])

    raw = (vwap - candle_df["close"]) / (vwap + candle_df["close"]).replace(0, np.nan)
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    lower = raw.quantile(lower_quantile)
    upper = raw.quantile(upper_quantile)
    clipped = raw.clip(lower=lower, upper=upper)

    if use_zscore:
        mean = clipped.mean()
        std = clipped.std()
        if std and not np.isnan(std):
            clipped = (clipped - mean) / std

    candle_df[factor_name] = clipped.clip(lower=-3, upper=3)
    return candle_df
