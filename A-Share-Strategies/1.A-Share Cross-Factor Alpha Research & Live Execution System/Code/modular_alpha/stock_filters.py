"""
Stock eligibility filters used before scoring and before order generation.

This file applies trading status, price trend, and profit quality filters to
the stock universe.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from .strategy_config import StrategyConfig
from .strategy_types import MarketDataApi, StrategyContextLike


class StockFilterEngine:
    """Evaluates whether a stock is eligible for ranking or trading."""

    def check_stock_eligibility(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
        config: StrategyConfig,
    ) -> bool:
        quotes = api.get_current_data()
        if stock not in quotes:
            return False
        quote = quotes[stock]
        if quote.paused or quote.last_price <= 0 or self.is_st_stock(api, stock):
            return False

        if config.filters.enable_rise_filter:
            short_rise = self.calculate_stock_rise(
                api,
                context,
                stock,
                config.filters.short_rise_period,
            )
            if short_rise is not None and short_rise >= config.filters.short_rise_threshold:
                return False

            long_rise = self.calculate_stock_rise(
                api,
                context,
                stock,
                config.filters.long_rise_period,
            )
            if long_rise is not None and long_rise >= config.filters.long_rise_threshold:
                return False

        if config.filters.enable_profit_drop_filter:
            profit_growth = self.calculate_profit_ttm_growth(api, context, stock)
            if (
                profit_growth is not None
                and profit_growth <= config.filters.profit_drop_threshold
            ):
                return False

        return True

    @staticmethod
    def is_st_stock(api: MarketDataApi, stock: str) -> bool:
        """Screens out ST and PT stocks using security display names."""

        info = api.get_security_info(stock)
        display_name = getattr(info, "display_name", "") or ""
        return "ST" in display_name or "*ST" in display_name or "PT" in display_name

    @staticmethod
    def calculate_profit_ttm_growth(
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
    ) -> Optional[float]:
        """Computes TTM net profit growth versus the previous year."""

        current_df = api.get_ttm_income(stock, context.current_dt, periods=4)
        if current_df.empty or "net_profit" not in current_df:
            return None
        current_ttm = float(current_df["net_profit"].sum())

        last_year_date = context.current_dt - timedelta(days=365)
        last_year_df = api.get_ttm_income(stock, last_year_date, periods=4)
        if last_year_df.empty or "net_profit" not in last_year_df:
            return None
        last_year_ttm = float(last_year_df["net_profit"].sum())
        if last_year_ttm <= 0:
            return -1.0
        return (current_ttm - last_year_ttm) / abs(last_year_ttm)

    @staticmethod
    def calculate_stock_rise(
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
        period: int,
    ) -> Optional[float]:
        """Computes cumulative return over the given lookback period."""

        end_date = context.current_dt
        start_date = end_date - timedelta(days=period + 10)
        price_df = api.get_price(
            stock,
            start_date=start_date,
            end_date=end_date,
            frequency="daily",
            fields=["close"],
            skip_paused=True,
            fq="pre",
        )
        if price_df.empty or len(price_df) < period:
            return None
        start_price = float(price_df["close"].iloc[-period])
        end_price = float(price_df["close"].iloc[-1])
        if start_price <= 0:
            return None
        return (end_price - start_price) / start_price
