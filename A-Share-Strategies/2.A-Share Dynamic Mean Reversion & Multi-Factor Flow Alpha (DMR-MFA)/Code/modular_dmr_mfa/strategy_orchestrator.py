"""
High-level orchestration for the Dynamic Mean Reversion & Multi-Factor Flow Alpha strategy.

The orchestrator wires together benchmark setup, pre-open bookkeeping, market
open capacity adjustment, candidate deployment, and intraday exit evaluation.
"""

from __future__ import annotations

import logging

from .portfolio_construction import PortfolioConstructionEngine
from .risk_controls import RiskControlEngine
from .strategy_config import StrategyConfig, build_default_strategy_config
from .strategy_types import StrategyRuntimeState, TargetValueOrder
from .technical_factors import TechnicalFactorLibrary


class DynamicMeanReversionFlowAlphaStrategy:
    """Coordinates the end-to-end workflow of the DMR-MFA trading strategy."""

    def __init__(
        self,
        config: StrategyConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config or build_default_strategy_config()
        self.logger = logger or logging.getLogger(__name__)
        self.state = StrategyRuntimeState(active_stock_num=self.config.regime.base_stock_num)

        self.technical_library = TechnicalFactorLibrary()
        self.portfolio_engine = PortfolioConstructionEngine(
            technical_library=self.technical_library,
            logger=self.logger,
        )
        self.risk_engine = RiskControlEngine(
            technical_library=self.technical_library,
            logger=self.logger,
        )

    def initialize(self, context) -> None:
        """Applies the benchmark and trading-cost configuration for the strategy."""

        set_benchmark(self.config.backtest.benchmark_code)
        set_option("use_real_price", self.config.backtest.use_real_price)
        set_slippage(FixedSlippage(self.config.backtest.fixed_slippage))
        set_order_cost(
            OrderCost(
                open_tax=self.config.backtest.open_tax,
                close_tax=self.config.backtest.close_tax,
                open_commission=self.config.backtest.open_commission,
                close_commission=self.config.backtest.close_commission,
                min_commission=self.config.backtest.min_commission,
            ),
            type="stock",
        )
        self.state.trading_day_counter = 0
        self.state.active_stock_num = self.config.regime.base_stock_num
        self.state.portfolio_high = None

    def before_market_open(self, context) -> None:
        """Records the latest portfolio peak before the session starts."""

        self.risk_engine.before_market_open(context, self.state)

    def market_open(self, context) -> list[TargetValueOrder]:
        """Runs the opening workflow of regime update, pruning, and redeployment."""

        self.state.trading_day_counter += 1
        self.portfolio_engine.update_target_stock_num(context, self.state, self.config)

        orders = self.portfolio_engine.build_pruning_orders(context, self.state)
        orders.extend(self.portfolio_engine.build_rebalance_orders(context, self.state, self.config))
        return orders

    def check_stop_loss_take_profit(self, context) -> list[TargetValueOrder]:
        """Runs the intraday exit evaluation for every live position."""

        return self.risk_engine.build_exit_orders(context, self.config)

    @staticmethod
    def after_market_close(context) -> None:
        """Retains the explicit post-close hook used by the strategy interface."""

        return None
