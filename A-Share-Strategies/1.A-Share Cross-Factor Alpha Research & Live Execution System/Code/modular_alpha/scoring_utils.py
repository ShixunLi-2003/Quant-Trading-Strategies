"""
Reusable scoring helpers for factor construction and order normalization.

This file contains shared functions for factor scoring, volatility conversion,
and order lot normalization.
"""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamps a value into a closed interval."""

    return max(minimum, min(maximum, value))


def calculate_range_score(
    value: float,
    optimal_range: tuple[float, float],
    max_score: float,
    reverse: bool = False,
) -> float:
    """
    Converts a continuous factor value into a bounded score.

    `reverse=True` is useful for factors such as volatility where lower values
    are preferable within a practical range.
    """

    low, high = optimal_range
    if reverse:
        if value <= low:
            return max_score
        if value >= high:
            return max_score * 0.10
        return max_score * (1 - (value - low) / (high - low))

    if low <= value <= high:
        return max_score
    if value < low:
        return max_score * (value / low) if low > 0 else max_score * 0.30
    return max_score * (high / value) if value > 0 else max_score * 0.30


def annualize_daily_volatility(daily_std: float, trading_days: int = 252) -> float:
    """Converts daily standard deviation to annualized volatility."""

    return daily_std * math.sqrt(trading_days)


def normalize_lot_size(quantity: int, lot_size: int = 100) -> int:
    """Rounds share quantity down to a tradable board lot."""

    if quantity <= 0:
        return 0
    return (quantity // lot_size) * lot_size


def latest_value(series: pd.Series) -> Optional[float]:
    """Safely extracts the latest scalar value from a pandas Series."""

    if series.empty:
        return None
    value = series.iloc[-1]
    if pd.isna(value):
        return None
    return float(value)
