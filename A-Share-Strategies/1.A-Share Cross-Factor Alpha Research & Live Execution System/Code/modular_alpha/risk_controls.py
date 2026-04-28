"""
Risk control module for intraday stop-loss, take-profit, and drawdown logic.

This file generates defensive target orders from position-level and
portfolio-level risk rules.
"""

from __future__ import annotations

from .scoring_utils import normalize_lot_size
from .strategy_config import StrategyConfig
from .strategy_types import StrategyContextLike, StrategyRuntimeState, TargetOrder, MarketDataApi


class RiskControlEngine:
    """Generates defensive target orders from position-level and portfolio-level rules."""

    def before_market_open(
        self,
        context: StrategyContextLike,
        state: StrategyRuntimeState,
    ) -> None:
        """Updates the running portfolio high watermark."""

        current_value = context.portfolio.total_value
        state.portfolio_high = max(state.portfolio_high, current_value)

    def generate_stop_loss_orders(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        config: StrategyConfig,
    ) -> list[TargetOrder]:
        """Builds partial or full exit orders based on unrealized PnL bands."""

        orders: list[TargetOrder] = []
        quotes = api.get_current_data()
        for stock, position in context.portfolio.positions.items():
            if stock not in quotes:
                continue
            quote = quotes[stock]
            if quote.paused or position.avg_cost <= 0:
                continue

            pnl = (quote.last_price - position.avg_cost) / position.avg_cost
            if config.risk.take_profit_threshold_1 <= pnl < config.risk.take_profit_threshold_2:
                target_shares = normalize_lot_size(
                    int(position.total_amount * 0.5),
                    config.portfolio.order_lot_size,
                )
                if target_shares > 0:
                    orders.append(
                        TargetOrder(
                            security=stock,
                            target_shares=target_shares,
                            delta_shares=target_shares - int(position.total_amount),
                            reason="take_profit_half",
                        )
                    )
            elif pnl >= config.risk.take_profit_threshold_2:
                orders.append(
                    TargetOrder(
                        security=stock,
                        target_value=0.0,
                        delta_shares=-int(position.total_amount),
                        reason="take_profit_full",
                    )
                )
            elif -config.risk.stop_loss_threshold_1 >= pnl > -config.risk.stop_loss_threshold_2:
                target_shares = normalize_lot_size(
                    int(position.total_amount * 0.5),
                    config.portfolio.order_lot_size,
                )
                if target_shares > 0:
                    orders.append(
                        TargetOrder(
                            security=stock,
                            target_shares=target_shares,
                            delta_shares=target_shares - int(position.total_amount),
                            reason="stop_loss_half",
                        )
                    )
            elif pnl <= -config.risk.stop_loss_threshold_2:
                orders.append(
                    TargetOrder(
                        security=stock,
                        target_value=0.0,
                        delta_shares=-int(position.total_amount),
                        reason="stop_loss_full",
                    )
                )
        return orders

    def check_max_drawdown(
        self,
        context: StrategyContextLike,
        state: StrategyRuntimeState,
        config: StrategyConfig,
    ) -> list[TargetOrder]:
        """Builds proportional reduction orders when drawdown breaches the trigger."""

        if state.portfolio_high <= 0:
            return []
        current_value = context.portfolio.total_value
        drawdown = (state.portfolio_high - current_value) / state.portfolio_high
        trigger = config.risk.max_drawdown_threshold * config.risk.max_drawdown_trigger_multiplier
        if drawdown <= trigger:
            return []
        return self.reduce_positions(
            context,
            reduce_ratio=config.risk.max_drawdown_reduce_ratio,
            lot_size=config.portfolio.order_lot_size,
        )

    @staticmethod
    def reduce_positions(
        context: StrategyContextLike,
        reduce_ratio: float,
        lot_size: int,
    ) -> list[TargetOrder]:
        """Produces portfolio-wide proportional cut orders."""

        reduction_orders: list[TargetOrder] = []
        for stock, position in context.portfolio.positions.items():
            target_shares = normalize_lot_size(
                int(position.total_amount * (1 - reduce_ratio)),
                lot_size,
            )
            reduction_orders.append(
                TargetOrder(
                    security=stock,
                    target_shares=target_shares,
                    delta_shares=target_shares - int(position.total_amount),
                    reason="portfolio_drawdown_reduction",
                )
            )
        return reduction_orders
