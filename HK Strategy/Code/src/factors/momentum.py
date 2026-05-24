from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from hk_quant.data.adapters import load_and_normalize_index_csv


def returns_momentum(market_data: dict[str, pd.DataFrame], window: int = 60) -> pd.DataFrame:
    close = market_data["close"]
    return close.pct_change(window, fill_method=None)


def price_vs_ma(market_data: dict[str, pd.DataFrame], window: int = 20) -> pd.DataFrame:
    close = market_data["close"]
    moving_average = close.rolling(window).mean()
    return close / moving_average - 1.0


def bbi_upturn_score(
    market_data: dict[str, pd.DataFrame],
    windows: tuple[int, int, int, int] = (3, 6, 12, 24),
    slope_window: int = 1,
    normalize_by_close: bool = True,
) -> pd.DataFrame:
    close = market_data["close"]
    rolling_means = [close.rolling(window=window, min_periods=window).mean() for window in windows]
    bbi = sum(rolling_means) / float(len(rolling_means))
    slope = bbi.diff(slope_window)
    if normalize_by_close:
        slope = slope / close.replace(0, np.nan)
    return slope


def obv_bottom_rising_score(
    market_data: dict[str, pd.DataFrame],
    lookback: int = 20,
    slope_window: int = 3,
    smooth_window: int = 3,
) -> pd.DataFrame:
    close = market_data["close"]
    volume = market_data["volume"].replace(0, np.nan)
    direction = np.sign(close.diff()).fillna(0.0)
    obv = (direction * volume.fillna(0.0)).cumsum()
    obv_smooth = obv.rolling(smooth_window, min_periods=smooth_window).mean()

    rolling_min = obv_smooth.rolling(lookback, min_periods=lookback).min()
    rolling_max = obv_smooth.rolling(lookback, min_periods=lookback).max()
    rolling_range = (rolling_max - rolling_min).replace(0, np.nan)

    # Favor names whose OBV has started turning up while still near the lower part of its recent range.
    bottom_proximity = 1.0 - ((obv_smooth - rolling_min) / rolling_range).clip(lower=0.0, upper=1.0)
    rising_strength = ((obv_smooth - obv_smooth.shift(slope_window)) / rolling_range).clip(lower=0.0)
    score = bottom_proximity * rising_strength
    return score.where(rolling_min.notna() & rolling_max.notna())


def obv_turn_volume_rebound_score(
    market_data: dict[str, pd.DataFrame],
    obv_lookback: int = 12,
    obv_slope_window: int = 3,
    volume_window: int = 10,
    smooth_window: int = 2,
    mild_ratio_center: float = 1.2,
    mild_ratio_width: float = 0.6,
) -> pd.DataFrame:
    close = market_data["close"]
    volume = market_data["volume"].replace(0, np.nan)
    amount = market_data["amount"].replace(0, np.nan)

    direction = np.sign(close.diff()).fillna(0.0)
    obv = (direction * volume.fillna(0.0)).cumsum()
    obv_smooth = obv.rolling(smooth_window, min_periods=smooth_window).mean()
    obv_floor = obv_smooth.rolling(obv_lookback, min_periods=obv_lookback).min()
    obv_ceiling = obv_smooth.rolling(obv_lookback, min_periods=obv_lookback).max()
    obv_range = (obv_ceiling - obv_floor).replace(0, np.nan)

    # OBV has started turning up while still in the lower half of its recent range.
    obv_bottom_proximity = 1.0 - ((obv_smooth - obv_floor) / obv_range).clip(lower=0.0, upper=1.0)
    obv_turn = ((obv_smooth - obv_smooth.shift(obv_slope_window)) / obv_range).clip(lower=0.0)

    amount_smooth = amount.rolling(smooth_window, min_periods=smooth_window).mean()
    amount_base = amount_smooth.rolling(volume_window, min_periods=volume_window).mean()
    volume_ratio = amount_smooth / amount_base.replace(0, np.nan)

    # Prefer mild expansion around the center, penalize both dry and explosive volume.
    mild_volume = (1.0 - ((volume_ratio - mild_ratio_center).abs() / max(mild_ratio_width, 1e-9))).clip(lower=0.0)
    recent_amount_trend = (amount_smooth / amount_smooth.shift(obv_slope_window) - 1.0).clip(lower=0.0)

    score = obv_bottom_proximity * obv_turn * mild_volume * (1.0 + recent_amount_trend)
    valid = obv_floor.notna() & obv_ceiling.notna() & amount_base.notna() & amount_smooth.notna()
    return score.where(valid)


def volatility_compression_score(
    market_data: dict[str, pd.DataFrame],
    short_window: int = 5,
    long_window: int = 20,
    trend_window: int = 20,
) -> pd.DataFrame:
    close = market_data["close"]
    returns = close.pct_change(fill_method=None)
    short_vol = returns.rolling(short_window, min_periods=short_window).std()
    long_vol = returns.rolling(long_window, min_periods=long_window).std()
    compression = 1.0 - (short_vol / long_vol.replace(0, np.nan))
    trend = close.pct_change(trend_window, fill_method=None)
    score = compression.clip(lower=0.0) * trend.where(trend > 0.0, 0.0)
    return score.where(short_vol.notna() & long_vol.notna() & trend.notna())


def volume_dryup_rebound_score(
    market_data: dict[str, pd.DataFrame],
    dryup_window: int = 15,
    rebound_window: int = 3,
    smooth_window: int = 3,
) -> pd.DataFrame:
    amount = market_data["amount"].replace(0, np.nan)
    smooth_amount = amount.rolling(smooth_window, min_periods=smooth_window).mean()
    dryup_floor = smooth_amount.rolling(dryup_window, min_periods=dryup_window).min()
    dryup_mean = smooth_amount.rolling(dryup_window, min_periods=dryup_window).mean()
    rebound_strength = smooth_amount / dryup_floor.replace(0, np.nan) - 1.0
    recent_change = smooth_amount / smooth_amount.shift(rebound_window) - 1.0
    dryup_quality = 1.0 - (smooth_amount / dryup_mean.replace(0, np.nan) - 1.0).clip(lower=0.0)
    score = rebound_strength.clip(lower=0.0) * recent_change.clip(lower=0.0) * dryup_quality.clip(lower=0.0)
    return score.where(dryup_floor.notna() & dryup_mean.notna() & recent_change.notna())


def relative_strength_vs_index(
    market_data: dict[str, pd.DataFrame],
    benchmark_path: str,
    window: int = 20,
    smooth_window: int = 3,
) -> pd.DataFrame:
    close = market_data["close"]
    benchmark = load_and_normalize_index_csv(Path(benchmark_path))["close"].rename("benchmark")
    benchmark = benchmark.reindex(close.index).ffill()
    stock_ret = close.pct_change(window, fill_method=None)
    bench_ret = benchmark.pct_change(window, fill_method=None)
    relative = stock_ret.sub(bench_ret, axis=0)
    if smooth_window > 1:
        relative = relative.rolling(smooth_window, min_periods=smooth_window).mean()
    return relative


def breakout_confirmation_score(
    market_data: dict[str, pd.DataFrame],
    breakout_window: int = 20,
    confirm_window: int = 5,
    ma_window: int = 20,
    stretch_cap: float = 0.08,
) -> pd.DataFrame:
    close = market_data["close"]
    rolling_high = close.rolling(breakout_window, min_periods=breakout_window).max().shift(1)
    ma = close.rolling(ma_window, min_periods=ma_window).mean()
    near_high = close / rolling_high.replace(0, np.nan) - 1.0
    short_momentum = close.pct_change(confirm_window, fill_method=None)
    ma_stretch = close / ma.replace(0, np.nan) - 1.0

    near_high_score = (1.0 - near_high.abs() / 0.08).clip(lower=0.0)
    momentum_score = short_momentum.where(short_momentum > 0.0, 0.0)
    stretch_penalty = (1.0 - (ma_stretch / stretch_cap)).clip(lower=0.0, upper=1.0)
    breakout_ok = (close >= rolling_high * 0.97) & (ma_stretch >= 0.0)
    score = near_high_score * momentum_score * stretch_penalty
    return score.where(breakout_ok & rolling_high.notna() & ma.notna())


def price_level(market_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return market_data["close"]


def amount_zscore(market_data: dict[str, pd.DataFrame], window: int = 20) -> pd.DataFrame:
    amount = market_data["amount"]
    rolling_mean = amount.rolling(window).mean()
    rolling_std = amount.rolling(window).std()
    return (amount - rolling_mean) / rolling_std.replace(0, np.nan)


def avg_amount_level(
    market_data: dict[str, pd.DataFrame],
    window: int = 20,
    log_transform: bool = True,
) -> pd.DataFrame:
    amount = market_data["amount"].replace(0, np.nan)
    avg_amount = amount.rolling(window, min_periods=window).mean()
    if log_transform:
        return np.log1p(avg_amount)
    return avg_amount


def realized_volatility(market_data: dict[str, pd.DataFrame], window: int = 20) -> pd.DataFrame:
    returns = market_data["close"].pct_change(fill_method=None)
    return returns.rolling(window).std() * np.sqrt(252)


def trend_compression_score(
    market_data: dict[str, pd.DataFrame],
    positive_window: int = 10,
    short_window: int = 3,
    min_short_return: float | None = -1.0,
    max_short_return: float | None = 0.02,
) -> pd.DataFrame:
    close = market_data["close"]
    medium_return = close.pct_change(positive_window, fill_method=None)
    short_return = close.pct_change(short_window, fill_method=None)

    positive_part = medium_return.where(medium_return > 0.0, 0.0)

    if min_short_return is not None and max_short_return is not None:
        in_band = (short_return >= min_short_return) & (short_return <= max_short_return)
        band_center = (min_short_return + max_short_return) / 2.0
        band_width = max(max_short_return - min_short_return, 1e-9)
        compression_part = (1.0 - (short_return - band_center).abs() / band_width).where(in_band, 0.0)
    elif max_short_return is not None:
        in_band = short_return <= max_short_return
        distance = (max_short_return - short_return).clip(lower=0.0)
        compression_part = (1.0 / (1.0 + distance.abs())).where(in_band, 0.0)
    elif min_short_return is not None:
        in_band = short_return >= min_short_return
        distance = (short_return - min_short_return).clip(lower=0.0)
        compression_part = (1.0 / (1.0 + distance.abs())).where(in_band, 0.0)
    else:
        compression_part = pd.DataFrame(1.0, index=short_return.index, columns=short_return.columns)

    score = positive_part + compression_part
    return score.where(medium_return.notna() & short_return.notna())
