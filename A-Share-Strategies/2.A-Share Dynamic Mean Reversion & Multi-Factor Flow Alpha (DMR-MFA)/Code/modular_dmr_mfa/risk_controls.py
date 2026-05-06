"""
Risk-control module for the Dynamic Mean Reversion & Multi-Factor Flow Alpha strategy.

This module maintains the portfolio high-water mark and evaluates the full-exit
rules driven by hard profit targets, hard stop-losses, OBV divergence, and BBI
trend deterioration.
"""

from __future__ import annotations

import logging

from .strategy_config import StrategyConfig
from .strategy_types import StrategyRuntimeState, TargetValueOrder
from .technical_factors import TechnicalFactorLibrary


class RiskControlEngine:
    """Produces full-liquidation target orders from the strategy exit rules."""

    def __init__(
        self,
        technical_library: TechnicalFactorLibrary,
        logger: logging.Logger | None = None,
    ) -> None:
        self.technical_library = technical_library
        self.logger = logger or logging.getLogger(__name__)

    def before_market_open(
        self,
        context,
        state: StrategyRuntimeState,
    ) -> None:
        """Updates the running net-asset-value peak before the session opens."""

        if state.portfolio_high is None:
            state.portfolio_high = context.portfolio.total_value
        else:
            state.portfolio_high = max(state.portfolio_high, context.portfolio.total_value)

    def build_exit_orders(
        self,
        context,
        config: StrategyConfig,
    ) -> list[TargetValueOrder]:
        """Evaluates every live position against the strategy exit cascade."""

        orders: list[TargetValueOrder] = []
        quotes = get_current_data()
        positions = context.portfolio.positions

        for stock in list(positions.keys()):
            position = positions[stock]
            if position.total_amount == 0:
                continue

            current_price = quotes[stock].last_price
            avg_cost = position.avg_cost
            if avg_cost <= 0:
                continue

            profit_rate = (current_price - avg_cost) / avg_cost

            if profit_rate >= config.risk.take_profit_pct:
                self.logger.info("Hard take-profit triggered | %s | pnl=%.2f%%", stock, profit_rate * 100.0)
                orders.append(TargetValueOrder(security=stock, target_value=0.0, reason="hard_take_profit"))
                continue

            if profit_rate > config.risk.obv_profit_floor:
                if self.technical_library.is_obv_stagnant(stock):
                    self.logger.info("OBV divergence exit | %s | early profit lock-in", stock)
                    orders.append(TargetValueOrder(security=stock, target_value=0.0, reason="obv_divergence_exit"))
                    continue

            if profit_rate <= config.risk.stop_loss_pct:
                self.logger.warning("Hard stop-loss triggered | %s | pnl=%.2f%%", stock, profit_rate * 100.0)
                orders.append(TargetValueOrder(security=stock, target_value=0.0, reason="hard_stop_loss"))
                continue

            if profit_rate <= config.risk.bbi_drawdown_floor:
                if self.technical_library.is_bbi_down(stock):
                    self.logger.warning(
                        "BBI dynamic exit | %s | drawdown and negative slope confirmed",
                        stock,
                    )
                    orders.append(TargetValueOrder(security=stock, target_value=0.0, reason="bbi_dynamic_exit"))

        return orders
