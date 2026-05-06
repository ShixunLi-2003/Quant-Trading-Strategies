"""
High-level orchestration module for the modular alpha strategy.

This file coordinates pre-market processing, rebalance logic, intraday risk
checks, and order forwarding.
"""

from __future__ import annotations

import logging

from .execution_bridge import QmtExecutionBridge
from .fundamental_factors import FundamentalFactorLibrary
from .industry_overlay import IndustryOverlayEngine
from .portfolio_construction import PortfolioConstructionEngine
from .risk_controls import RiskControlEngine
from .stock_filters import StockFilterEngine
from .strategy_config import StrategyConfig, build_default_strategy_config
from .strategy_types import StrategyRuntimeState, TargetOrder, TradeSignal, MarketDataApi, StrategyContextLike
from .technical_factors import TechnicalFactorLibrary


class CrossFactorAlphaResearchStrategy:
    """Coordinates the main strategy workflow."""

    def __init__(
        self,
        config: StrategyConfig | None = None,
        execution_bridge: QmtExecutionBridge | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config or build_default_strategy_config()
        self.logger = logger or logging.getLogger(__name__)
        self.state = StrategyRuntimeState()
        self.execution_bridge = execution_bridge

        self.filter_engine = StockFilterEngine()
        self.overlay_engine = IndustryOverlayEngine()
        self.technical_library = TechnicalFactorLibrary()
        self.fundamental_library = FundamentalFactorLibrary()
        self.portfolio_engine = PortfolioConstructionEngine(
            technical_library=self.technical_library,
            fundamental_library=self.fundamental_library,
            overlay_engine=self.overlay_engine,
            filter_engine=self.filter_engine,
            logger=self.logger,
        )
        self.risk_engine = RiskControlEngine()

    def before_market_open(self, context: StrategyContextLike) -> None:
        """Pre-open bookkeeping hook."""

        if self.state.portfolio_high == 0:
            self.state.portfolio_high = context.portfolio.total_value
        self.risk_engine.before_market_open(context, self.state)

    def market_open_rebalance(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
    ) -> list[TargetOrder]:
        """Runs the main stock selection and target order generation pipeline."""

        self.state.trading_day_counter += 1
        self.portfolio_engine.adjust_dynamic_weights(
            api,
            context,
            self.config,
            self.state.dynamic_weight,
        )
        if self.state.trading_day_counter % self.state.dynamic_weight.rebalance_days != 1:
            return []

        universe = api.get_index_stocks(
            self.config.portfolio.benchmark_code,
            date=context.current_dt,
        )
        scored = self.portfolio_engine.calculate_comprehensive_scores(
            api,
            context,
            universe,
            self.config,
            self.state.dynamic_weight,
        )
        if scored.empty:
            return []

        selected = self.portfolio_engine.select_top_stocks(
            api,
            context,
            scored,
            self.config,
        )
        return self.portfolio_engine.build_target_orders(
            api,
            context,
            selected,
            self.config,
            self.state.dynamic_weight,
        )

    def market_open_stop_loss(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
    ) -> list[TargetOrder]:
        """Runs the intraday defensive checks."""

        orders = self.risk_engine.generate_stop_loss_orders(api, context, self.config)
        orders.extend(self.risk_engine.check_max_drawdown(context, self.state, self.config))
        return orders

    def after_market_close(self, context: StrategyContextLike) -> float | None:
        """Computes and records the daily return."""

        daily_return = None
        if self.state.last_portfolio_value and self.state.last_portfolio_value > 0:
            daily_return = (
                context.portfolio.total_value - self.state.last_portfolio_value
            ) / self.state.last_portfolio_value
        self.state.last_portfolio_value = context.portfolio.total_value
        return daily_return

    def forward_orders(
        self,
        api: MarketDataApi,
        orders: list[TargetOrder],
    ) -> list[dict]:
        """
        Converts target orders into bridge signals.
        """

        if self.execution_bridge is None:
            return []

        quotes = api.get_current_data()
        responses: list[dict] = []
        for order in orders:
            if order.delta_shares == 0 or order.security not in quotes:
                continue
            quote = quotes[order.security]
            signal = TradeSignal(
                security=order.security,
                is_buy=order.delta_shares > 0,
                quantity=abs(order.delta_shares),
                price=float(quote.last_price),
                reason=order.reason,
            )
            responses.append(self.execution_bridge.send_signal(signal))
        return responses
