"""
Performance Metrics

Computes return, volatility, Sharpe, drawdown, and related portfolio statistics.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def calculate_drawdown_series(equity_curve: pd.Series) -> pd.Series:
    running_max = equity_curve.cummax()
    return equity_curve / running_max - 1.0


def calculate_performance_metrics(
    returns: pd.Series,
    equity_curve: pd.Series | None = None,
    periods_per_year: int = 252,
) -> dict[str, float]:
    clean_returns = returns.dropna().astype(float)
    if clean_returns.empty:
        return {}

    if equity_curve is None:
        equity_curve = (1.0 + clean_returns).cumprod()
    drawdown = calculate_drawdown_series(equity_curve)
    if len(equity_curve) > 1 and equity_curve.iloc[0] > 0 and equity_curve.iloc[-1] > 0:
        total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0
        annual_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (periods_per_year / len(clean_returns)) - 1.0
    else:
        total_return = float("nan")
        annual_return = float("nan")
    annual_volatility = clean_returns.std(ddof=0) * math.sqrt(periods_per_year)
    sharpe = annual_return / annual_volatility if annual_volatility and not np.isnan(annual_volatility) else np.nan
    max_drawdown = drawdown.min()
    calmar = annual_return / abs(max_drawdown) if max_drawdown and not np.isnan(max_drawdown) else np.nan
    win_rate = float((clean_returns > 0).mean())

    return {
        "total_return": float(total_return),
        "annual_return": float(annual_return),
        "annual_volatility": float(annual_volatility),
        "sharpe": float(sharpe) if not np.isnan(sharpe) else None,
        "max_drawdown": float(max_drawdown),
        "calmar": float(calmar) if not np.isnan(calmar) else None,
        "win_rate": win_rate,
        "trading_days": int(clean_returns.shape[0]),
    }
