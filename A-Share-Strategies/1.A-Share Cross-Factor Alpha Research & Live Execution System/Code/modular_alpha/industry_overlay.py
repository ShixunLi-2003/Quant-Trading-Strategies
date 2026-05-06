"""
Industry sentiment and region overlay logic for the stock ranking pipeline.

This file calculates industry bonus scores, region bonus scores, and sector
boom checks used during stock selection.
"""

from __future__ import annotations

from datetime import timedelta

from .strategy_config import StrategyConfig
from .strategy_types import DynamicWeightState, MarketDataApi, StrategyContextLike


class IndustryOverlayEngine:
    """Computes sector bonus scores and sector boom eligibility."""

    def __init__(self) -> None:
        self._industry_cache: dict[str, dict] = {}
        self._region_cache: dict[str, str] = {}

    def calculate_industry_score(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
        config: StrategyConfig,
        dynamic_weight: DynamicWeightState,
    ) -> float:
        """Assigns regime-aware industry bonus scores."""

        industry_name = self._get_industry_name(api, context, stock)
        if not industry_name:
            return 0.0

        for avoid_keyword in config.industry.avoid_industries:
            if avoid_keyword in industry_name:
                return -5.0

        market_status = dynamic_weight.market_status
        for keyword in config.industry.growth_industries:
            if keyword in industry_name:
                score = config.industry.bonus_scores["growth"]
                if market_status == "bull":
                    score *= 1.2
                elif market_status == "bear":
                    score *= 0.8
                return score

        for keyword in config.industry.value_industries:
            if keyword in industry_name:
                score = config.industry.bonus_scores["value"]
                if market_status == "bear":
                    score *= 1.2
                elif market_status == "bull":
                    score *= 0.9
                return score

        for keyword in config.industry.cyclical_industries:
            if keyword in industry_name:
                return config.industry.bonus_scores["cyclical"]
        return 0.0

    def calculate_region_score(
        self,
        api: MarketDataApi,
        stock: str,
        config: StrategyConfig,
    ) -> float:
        """Applies a region bonus based on security naming metadata."""

        if stock not in self._region_cache:
            info = api.get_security_info(stock)
            self._region_cache[stock] = getattr(info, "name", "") or ""
        security_name = self._region_cache[stock]
        for region_keyword, bonus in config.industry.region_bonus.items():
            if region_keyword in security_name:
                return bonus
        return 0.0

    def check_single_stock_boom(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
        config: StrategyConfig,
    ) -> bool:
        """Checks whether the stock's mapped sector proxy is in a positive regime."""

        if not config.industry.enable_boom_check:
            return True

        industry_name = self._get_industry_name(api, context, stock)
        if not industry_name:
            return True

        target_symbol = None
        for keyword, proxy_symbol in config.industry.boom_proxy_map.items():
            if keyword in industry_name:
                target_symbol = proxy_symbol
                break
        if not target_symbol:
            return True

        if len(target_symbol) <= 3:
            target_symbol = api.get_dominant_future(target_symbol) or target_symbol

        end_date = context.current_dt
        start_date = end_date - timedelta(days=config.industry.boom_check_period + 10)
        proxy_prices = api.get_price(
            target_symbol,
            start_date=start_date,
            end_date=end_date,
            frequency="daily",
            fields=["close"],
        )
        if proxy_prices.empty or len(proxy_prices) < config.industry.boom_check_period:
            return True

        base_price = float(proxy_prices["close"].iloc[-config.industry.boom_check_period])
        latest_price = float(proxy_prices["close"].iloc[-1])
        if base_price <= 0:
            return True
        momentum = (latest_price - base_price) / base_price
        return momentum >= config.industry.boom_pass_threshold

    def _get_industry_name(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
    ) -> str:
        if stock not in self._industry_cache:
            self._industry_cache[stock] = api.get_industry(stock, date=context.current_dt)
        industry_data = self._industry_cache[stock]
        if not industry_data:
            return ""
        for info in industry_data.values():
            if isinstance(info, dict) and "industry_name" in info:
                return str(info["industry_name"])
        return ""
