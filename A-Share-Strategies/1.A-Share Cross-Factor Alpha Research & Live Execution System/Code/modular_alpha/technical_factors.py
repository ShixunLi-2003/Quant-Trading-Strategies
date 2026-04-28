"""
Technical factor library for short-to-medium horizon stock selection.

This file calculates momentum, volatility, volume ratio, RSI, and breakout
scores from daily price and volume data.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from .scoring_utils import annualize_daily_volatility, calculate_range_score, latest_value
from .strategy_config import StrategyConfig
from .strategy_types import MarketDataApi, StrategyContextLike


class TechnicalFactorLibrary:
    """Calculates technical factor scores for one stock at a time."""

    def calculate_scores(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
        config: StrategyConfig,
    ) -> dict[str, float]:
        technical = config.technical
        max_window = max(
            technical.momentum_window,
            technical.volatility_window,
            technical.volume_ratio_windows[1],
            technical.rsi_window,
            technical.breakout_window,
        )
        end_date = context.current_dt
        start_date = end_date - timedelta(days=max_window + 30)
        prices = api.get_price(
            stock,
            start_date=start_date,
            end_date=end_date,
            frequency="daily",
            fields=["close", "high", "low", "volume"],
            skip_paused=True,
            fq="pre",
        )
        if prices is None or len(prices) < max_window:
            return {}

        close = prices["close"].astype(float)
        high = prices["high"].astype(float)
        volume = prices["volume"].astype(float)
        scores: dict[str, float] = {}

        momentum_rule = technical.rules["momentum"]
        momentum = (close.iloc[-1] / close.iloc[-technical.momentum_window]) - 1
        scores["momentum_score"] = calculate_range_score(
            momentum,
            momentum_rule.optimal_range,
            momentum_rule.weight,
        )

        volatility_rule = technical.rules["volatility"]
        returns = np.log(close / close.shift(1)).dropna()
        if len(returns) >= technical.volatility_window:
            rolling_std = returns.rolling(technical.volatility_window).std()
            daily_std = latest_value(rolling_std)
            if daily_std is not None:
                annualized_vol = annualize_daily_volatility(daily_std)
                scores["volatility_score"] = calculate_range_score(
                    annualized_vol,
                    volatility_rule.optimal_range,
                    volatility_rule.weight,
                    reverse=True,
                )

        volume_rule = technical.rules["volume_ratio"]
        short_window, long_window = technical.volume_ratio_windows
        long_avg = latest_value(volume.rolling(long_window).mean())
        short_avg = latest_value(volume.rolling(short_window).mean())
        if long_avg is not None and short_avg is not None:
            volume_ratio = short_avg / long_avg if long_avg != 0 else 1.0
            scores["volume_ratio_score"] = calculate_range_score(
                volume_ratio,
                volume_rule.optimal_range,
                volume_rule.weight,
            )

        rsi_rule = technical.rules["rsi"]
        if len(close) >= technical.rsi_window:
            delta = close.diff()
            gains = delta.clip(lower=0).rolling(technical.rsi_window).mean()
            losses = (-delta.clip(upper=0)).rolling(technical.rsi_window).mean()
            latest_gain = latest_value(gains)
            latest_loss = latest_value(losses)
            if latest_gain is not None and latest_loss is not None:
                if latest_loss == 0:
                    rsi_value = 100.0 if latest_gain > 0 else 50.0
                else:
                    relative_strength = latest_gain / latest_loss
                    rsi_value = 100 - (100 / (1 + relative_strength))
                scores["rsi_score"] = calculate_range_score(
                    rsi_value,
                    rsi_rule.optimal_range,
                    rsi_rule.weight,
                )

        breakout_rule = technical.rules["breakout"]
        if len(close) >= technical.breakout_window:
            recent_high = high.rolling(technical.breakout_window).max().iloc[-2]
            if not pd.isna(recent_high) and recent_high > 0:
                breakout = (close.iloc[-1] - recent_high) / recent_high
                scores["breakout_score"] = (
                    breakout_rule.weight if breakout >= breakout_rule.threshold else 0.0
                )

        return scores
