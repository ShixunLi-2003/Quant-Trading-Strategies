from __future__ import annotations

import numpy as np
import pandas as pd


def ma_cross_signal(close: pd.Series | pd.DataFrame, fast: int = 20, slow: int = 60):
    fast_ma = close.rolling(fast).mean()
    slow_ma = close.rolling(slow).mean()
    return fast_ma > slow_ma


def breakout_signal(close: pd.Series | pd.DataFrame, window: int = 20):
    breakout_level = close.rolling(window).max().shift(1)
    return close > breakout_level


def equity_ma_timing_signal(equity_curve: pd.Series, window: int = 20) -> pd.Series:
    equity = pd.Series(equity_curve).astype(float)
    ma = equity.rolling(window, min_periods=1).mean()
    signal = (equity > ma).astype(float)
    return signal.reindex(equity.index).fillna(0.0)


def light_equity_ma_risk_signal(
    equity_curve: pd.Series,
    window: int = 20,
    above_exposure: float = 1.0,
    below_exposure: float = 0.7,
) -> pd.Series:
    equity = pd.Series(equity_curve).astype(float)
    ma = equity.rolling(window, min_periods=1).mean()
    signal = pd.Series(below_exposure, index=equity.index, dtype=float)
    signal.loc[equity > ma] = above_exposure
    return signal.reindex(equity.index).ffill().fillna(above_exposure)


def index_ma_risk_signal(
    price_series: pd.Series,
    window: int = 60,
    above_exposure: float = 1.0,
    below_exposure: float = 0.5,
) -> pd.Series:
    price = pd.Series(price_series).astype(float)
    ma = price.rolling(window, min_periods=1).mean()
    signal = pd.Series(below_exposure, index=price.index, dtype=float)
    signal.loc[price > ma] = above_exposure
    return signal.reindex(price.index).ffill().fillna(above_exposure)


def sharpe_decay_timing_signal(
    equity_curve: pd.Series,
    short_window: int = 20,
    mid_window: int = 60,
    long_window: int = 120,
    smooth_window: int = 3,
) -> pd.Series:
    equity = pd.Series(equity_curve).astype(float)
    returns = equity.pct_change(fill_method=None)

    def rolling_sharpe(series: pd.Series, window: int) -> pd.Series:
        mean_return = series.rolling(window, min_periods=min(10, window)).mean()
        std_return = series.rolling(window, min_periods=min(10, window)).std()
        return mean_return / (std_return + 1e-10) * np.sqrt(252)

    short_sharpe = rolling_sharpe(returns, short_window)
    mid_sharpe = rolling_sharpe(returns, mid_window)
    long_sharpe = rolling_sharpe(returns, long_window)

    decay_mid = short_sharpe - mid_sharpe
    decay_long = short_sharpe - long_sharpe
    decay = 0.8 * decay_mid + 0.2 * decay_long

    signal = pd.Series(1.0, index=equity.index)
    signal[(decay <= 0.0) & (decay >= -0.3)] = 0.85
    signal[(decay < -0.3) & (decay >= -0.8)] = 0.5
    signal[decay < -0.8] = 0.25
    signal = signal.rolling(smooth_window, min_periods=1).mean()
    return signal.ffill().fillna(1.0)
