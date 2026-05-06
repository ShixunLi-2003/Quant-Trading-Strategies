"""
Portfolio construction engine for the modular alpha strategy.

This file handles regime adjustment, stock ranking, candidate selection, and
target position generation.
"""

from __future__ import annotations

from datetime import timedelta
import logging

import pandas as pd

from .industry_overlay import IndustryOverlayEngine
from .scoring_utils import normalize_lot_size
from .stock_filters import StockFilterEngine
from .strategy_config import StrategyConfig
from .strategy_types import DynamicWeightState, TargetOrder, MarketDataApi, StrategyContextLike
from .technical_factors import TechnicalFactorLibrary
from .fundamental_factors import FundamentalFactorLibrary


class PortfolioConstructionEngine:
    """Builds ranked candidate lists and target position instructions."""

    def __init__(
        self,
        technical_library: TechnicalFactorLibrary,
        fundamental_library: FundamentalFactorLibrary,
        overlay_engine: IndustryOverlayEngine,
        filter_engine: StockFilterEngine,
        logger: logging.Logger | None = None,
    ) -> None:
        self.technical_library = technical_library
        self.fundamental_library = fundamental_library
        self.overlay_engine = overlay_engine
        self.filter_engine = filter_engine
        self.logger = logger or logging.getLogger(__name__)

    def adjust_dynamic_weights(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        config: StrategyConfig,
        state: DynamicWeightState,
    ) -> DynamicWeightState:
        """Updates regime multipliers and rebalance cadence from benchmark momentum."""

        benchmark_return = self.get_benchmark_returns(
            api,
            context,
            config.portfolio.benchmark_code,
        )
        if benchmark_return > 0.05:
            state.market_status = "bull"
            state.tech_weight_multiplier = 1.20
            state.fundamental_weight_multiplier = 0.90
            state.rebalance_days = config.portfolio.rebalance_days_bull
        elif benchmark_return < -0.05:
            state.market_status = "bear"
            state.tech_weight_multiplier = 0.80
            state.fundamental_weight_multiplier = 1.20
            state.rebalance_days = config.portfolio.rebalance_days_bear
        else:
            state.market_status = "normal"
            state.tech_weight_multiplier = 1.00
            state.fundamental_weight_multiplier = 1.00
            state.rebalance_days = config.portfolio.rebalance_days_normal
        return state

    def get_benchmark_returns(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        benchmark_code: str,
        days: int = 20,
    ) -> float:
        """Computes rolling benchmark return for regime detection."""

        end_date = context.current_dt
        start_date = end_date - timedelta(days=days + 10)
        prices = api.get_price(
            benchmark_code,
            start_date=start_date,
            end_date=end_date,
            frequency="daily",
            fields=["close"],
        )
        if prices.empty or len(prices) < days:
            return 0.0
        base_price = float(prices["close"].iloc[-days])
        latest_price = float(prices["close"].iloc[-1])
        if base_price <= 0:
            return 0.0
        return (latest_price - base_price) / base_price

    def calculate_comprehensive_scores(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock_list: list[str],
        config: StrategyConfig,
        state: DynamicWeightState,
    ) -> pd.DataFrame:
        """Builds a score table for the filtered stock universe."""

        records: list[dict[str, float | str]] = []
        for stock in stock_list:
            if not self.filter_engine.check_stock_eligibility(api, context, stock, config):
                continue

            technical_scores = self.technical_library.calculate_scores(api, context, stock, config)
            technical_total = sum(technical_scores.values()) * state.tech_weight_multiplier

            fundamental_scores = self.fundamental_library.calculate_scores(
                api,
                context,
                stock,
                config,
            )
            fundamental_total = sum(fundamental_scores.values()) * state.fundamental_weight_multiplier

            industry_bonus = self.overlay_engine.calculate_industry_score(
                api,
                context,
                stock,
                config,
                state,
            )
            region_bonus = self.overlay_engine.calculate_region_score(api, stock, config)

            total_score = technical_total + fundamental_total + industry_bonus + region_bonus
            record: dict[str, float | str] = {
                "stock": stock,
                "technical_total": technical_total,
                "fundamental_total": fundamental_total,
                "industry_bonus": industry_bonus,
                "region_bonus": region_bonus,
                "total_score": total_score,
            }
            record.update(technical_scores)
            record.update(fundamental_scores)
            records.append(record)

        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records).set_index("stock").sort_values("total_score", ascending=False)

    def select_top_stocks(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        scored_stocks: pd.DataFrame,
        config: StrategyConfig,
    ) -> list[str]:
        """
        Selects top-ranked stocks that pass the boom check.
        """

        selected: list[str] = []
        for stock in scored_stocks.index.tolist():
            if len(selected) >= config.portfolio.stock_num:
                break
            if not self.filter_engine.check_stock_eligibility(api, context, stock, config):
                continue
            if self.overlay_engine.check_single_stock_boom(api, context, stock, config):
                selected.append(stock)
        return selected

    def build_target_orders(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        selected_stocks: list[str],
        config: StrategyConfig,
        state: DynamicWeightState,
    ) -> list[TargetOrder]:
        """Builds normalized target orders for the rebalance cycle."""

        if not selected_stocks:
            return []

        orders: list[TargetOrder] = []
        current_positions = context.portfolio.positions
        total_value = context.portfolio.total_value
        target_value = min(
            total_value / len(selected_stocks),
            total_value * config.portfolio.max_position_per_stock,
        )
        quotes = api.get_current_data()

        for stock in list(current_positions.keys()):
            if stock not in selected_stocks:
                orders.append(
                    TargetOrder(
                        security=stock,
                        target_value=0.0,
                        delta_shares=-int(current_positions[stock].total_amount),
                        reason="not_selected_anymore",
                    )
                )

        for stock in selected_stocks:
            if stock not in quotes:
                continue
            quote = quotes[stock]
            if quote.last_price <= 0:
                continue
            current_value = current_positions[stock].value if stock in current_positions else 0.0
            diff_value = target_value - current_value
            min_trade_value = (
                quote.last_price
                * config.portfolio.order_lot_size
                * config.portfolio.order_diff_buffer_ratio
            )
            threshold_multiplier = (
                config.portfolio.bear_market_buffer_multiplier
                if state.market_status == "bear"
                else 1.0
            )
            if abs(diff_value) <= min_trade_value * threshold_multiplier:
                continue

            delta_shares = normalize_lot_size(
                int(diff_value / quote.last_price),
                config.portfolio.order_lot_size,
            )
            if delta_shares == 0:
                continue
            orders.append(
                TargetOrder(
                    security=stock,
                    target_value=target_value,
                    delta_shares=delta_shares,
                    reason="rebalance_target",
                )
            )

        self.logger.info("Built %s target orders.", len(orders))
        return orders
