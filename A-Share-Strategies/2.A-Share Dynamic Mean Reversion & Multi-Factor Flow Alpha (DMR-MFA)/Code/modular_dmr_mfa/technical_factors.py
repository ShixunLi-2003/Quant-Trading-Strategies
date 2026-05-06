"""
Technical diagnostics for the Dynamic Mean Reversion & Multi-Factor Flow Alpha strategy.

This module implements the benchmark Bollinger regime classifier together with
the OBV divergence check and the BBI slope confirmation used by the exit logic.
"""

from __future__ import annotations

import numpy as np

from .strategy_config import StrategyConfig


class TechnicalFactorLibrary:
    """Provides the benchmark and position-level technical checks used by the strategy."""

    def get_bollinger_regime(
        self,
        context,
        config: StrategyConfig,
    ) -> str:
        """Determines the benchmark regime from the HS300 Bollinger band position."""

        try:
            df = attribute_history(
                config.backtest.benchmark_code,
                config.regime.bollinger_period + 1,
                "1d",
                ["close"],
                skip_paused=True,
                df=True,
            )
            if df is None or len(df) < config.regime.bollinger_period + 1:
                return "neutral"

            closes = df["close"].values
            moving_average = np.mean(closes[:-1])
            rolling_std = np.std(closes[:-1])
            upper_band = moving_average + config.regime.bollinger_std_multiplier * rolling_std
            lower_band = moving_average - config.regime.bollinger_std_multiplier * rolling_std
            current_price = closes[-1]

            if current_price > upper_band:
                return "up"
            if current_price < lower_band:
                return "down"
            return "neutral"
        except Exception as exc:
            log.warn("Regime detection error: %s", exc)
            return "neutral"

    def is_obv_stagnant(self, stock: str) -> bool:
        """Checks whether OBV reaches a short-term high while price fails to confirm."""

        try:
            df = attribute_history(stock, 10, "1d", ["close", "volume"])
            if len(df) < 5:
                return False

            price_diff = df["close"].diff()
            direction = price_diff.apply(lambda value: 1 if value > 0 else (-1 if value < 0 else 0))
            obv = (direction * df["volume"]).fillna(0).cumsum()

            return (obv.iloc[-1] > obv.iloc[-6:-1].max()) and (
                df["close"].iloc[-1] <= df["close"].iloc[-6:-1].max()
            )
        except Exception:
            return False

    def is_bbi_down(self, stock: str) -> bool:
        """Checks whether the BBI composite average is sloping downward."""

        try:
            df = attribute_history(stock, 30, "1d", ["close"])
            if len(df) < 24:
                return False

            def bbi_value(values):
                return (
                    values[-10:].mean()
                    + values[-20:].mean()
                    + values[-30:].mean()
                    + values[-60:].mean()
                ) / 4.0

            closes = df["close"].values
            current_bbi = bbi_value(closes)
            previous_bbi = bbi_value(closes[:-1])
            return current_bbi < previous_bbi
        except Exception:
            return False
