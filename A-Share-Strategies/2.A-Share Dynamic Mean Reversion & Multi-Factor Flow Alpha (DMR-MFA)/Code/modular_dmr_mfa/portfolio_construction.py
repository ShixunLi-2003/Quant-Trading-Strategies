"""
Portfolio construction engine for the Dynamic Mean Reversion & Multi-Factor Flow Alpha strategy.

This module manages the daily capacity target, ranking of oversold rebound
candidates, pruning of existing holdings, and deployment of available cash.
"""

from __future__ import annotations

import logging

from jqdata import get_money_flow

from .strategy_config import StrategyConfig
from .strategy_types import StrategyRuntimeState, TargetValueOrder
from .technical_factors import TechnicalFactorLibrary


class PortfolioConstructionEngine:
    """Builds target-value orders for capacity control and stock deployment."""

    def __init__(
        self,
        technical_library: TechnicalFactorLibrary,
        logger: logging.Logger | None = None,
    ) -> None:
        self.technical_library = technical_library
        self.logger = logger or logging.getLogger(__name__)

    def update_target_stock_num(
        self,
        context,
        state: StrategyRuntimeState,
        config: StrategyConfig,
    ) -> None:
        """Updates the active holding count from the benchmark Bollinger regime."""

        status = self.technical_library.get_bollinger_regime(context, config)
        if status == "up":
            new_num = config.regime.max_stock_num
        elif status == "down":
            new_num = config.regime.min_stock_num
        else:
            new_num = config.regime.base_stock_num

        if new_num != state.active_stock_num:
            self.logger.info(
                "Market regime %s | target capacity %s -> %s",
                status,
                state.active_stock_num,
                new_num,
            )
            state.active_stock_num = new_num

    def build_pruning_orders(
        self,
        context,
        state: StrategyRuntimeState,
    ) -> list[TargetValueOrder]:
        """Generates liquidation orders when holdings exceed the active capacity."""

        current_holdings = [
            (stock, position)
            for stock, position in context.portfolio.positions.items()
            if position.total_amount > 0
        ]
        current_count = len(current_holdings)
        if current_count <= state.active_stock_num:
            return []

        sell_num = current_count - state.active_stock_num
        quotes = get_current_data()
        stock_profit = []
        for stock, position in current_holdings:
            avg_cost = position.avg_cost
            if avg_cost <= 0:
                profit_rate = 0
            else:
                current_price = quotes[stock].last_price
                profit_rate = (current_price - avg_cost) / avg_cost
            stock_profit.append((stock, profit_rate))

        stock_profit.sort(key=lambda item: item[1])
        return [
            TargetValueOrder(security=stock, target_value=0.0, reason="capacity_pruning")
            for stock, _ in stock_profit[:sell_num]
        ]

    def build_rebalance_orders(
        self,
        context,
        state: StrategyRuntimeState,
        config: StrategyConfig,
    ) -> list[TargetValueOrder]:
        """Generates equal-value buy orders to restore the active capacity."""

        current_holdings = [
            stock
            for stock, position in context.portfolio.positions.items()
            if position.total_amount > 0
        ]
        current_count = len(current_holdings)
        if current_count >= state.active_stock_num:
            return []

        need_buy = state.active_stock_num - current_count
        candidates = self.select_best_stocks(context, config)
        candidates = [stock for stock in candidates if stock not in current_holdings]
        if len(candidates) == 0:
            return []

        to_buy = candidates[:need_buy]
        cash = context.portfolio.available_cash
        if cash <= 0:
            return []

        per_value = cash / len(to_buy)
        return [
            TargetValueOrder(security=stock, target_value=per_value, reason="equal_cash_deployment")
            for stock in to_buy
        ]

    def select_best_stocks(
        self,
        context,
        config: StrategyConfig,
    ) -> list[str]:
        """Ranks candidates by the magnitude of the qualifying short-term drawdown."""

        candidates = []
        current_data = get_current_data()

        for stock in config.signal.stock_pool:
            quote = current_data[stock]
            if quote.paused:
                continue

            try:
                money_flow = get_money_flow(stock, count=1, end_date=context.current_dt)
                if money_flow is None or len(money_flow) == 0:
                    continue
                net_main = money_flow["net_amount_main"].iloc[-1]
                if net_main <= 0:
                    continue
            except Exception:
                continue

            try:
                df = attribute_history(
                    stock,
                    config.signal.lookback_days + config.signal.drop_days + 1,
                    "1d",
                    ["close"],
                    skip_paused=True,
                    df=True,
                )
                if df is None or len(df) < config.signal.lookback_days + config.signal.drop_days:
                    continue

                close = df["close"].values
                is_down_10d = close[-1] < close[-1 - config.signal.lookback_days]
                drop_3d = (
                    close[-1] - close[-1 - config.signal.drop_days]
                ) / close[-1 - config.signal.drop_days]

                if is_down_10d and drop_3d < config.signal.drop_threshold:
                    candidates.append((stock, drop_3d))
            except Exception:
                continue

        candidates.sort(key=lambda item: item[1])
        return [stock for stock, _ in candidates]
