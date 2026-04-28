"""
Fundamental factor library for valuation and quality scoring.

This file calculates valuation, growth, profitability, leverage, and size
scores from financial statement and forecast data.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from .strategy_config import FactorRule, StrategyConfig
from .strategy_types import MarketDataApi, StrategyContextLike


class FundamentalFactorLibrary:
    """Calculates valuation, growth, and quality scores for one stock."""

    def calculate_scores(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
        config: StrategyConfig,
    ) -> dict[str, float]:
        rules = config.fundamental.rules
        scores: dict[str, float] = {}

        pe = self.calculate_ttm_pe(api, context, stock)
        scores["pe_ratio_score"] = self._score_pe_ratio(pe, rules["pe_ratio"])

        expected_growth = self.calculate_expected_growth(api, context, stock)
        scores["expected_growth_score"] = self._score_growth(
            expected_growth,
            rules["expected_growth"],
        )

        net_profit_growth = self.calculate_net_profit_ttm_growth(api, context, stock)
        scores["net_profit_ttm_growth_score"] = self._score_growth(
            net_profit_growth,
            rules["net_profit_ttm_growth"],
        )

        financials = self.get_enhanced_financial_data(api, context, stock)
        if not financials:
            return scores

        scores["gross_margin_score"] = self._score_gross_margin(
            financials.get("gross_margin"),
            rules["gross_margin"],
        )
        scores["debt_ratio_score"] = self._score_debt_ratio(
            financials.get("debt_ratio"),
            rules["debt_ratio"],
        )
        scores["market_cap_score"] = self._score_market_cap(
            financials.get("market_cap"),
            rules["market_cap"],
        )
        return scores

    def calculate_ttm_pe(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
    ) -> Optional[float]:
        """Computes TTM PE from TTM profit and current market capitalization."""

        income_df = api.get_ttm_income(stock, context.current_dt, periods=4)
        if income_df.empty or "net_profit" not in income_df:
            return None
        ttm_profit = float(income_df["net_profit"].sum())
        if ttm_profit <= 0:
            return None

        valuation_df = api.get_valuation(stock, context.current_dt)
        if valuation_df.empty or "market_cap" not in valuation_df:
            return None
        market_cap = float(valuation_df["market_cap"].iloc[0]) * 100000000
        return market_cap / ttm_profit

    def calculate_expected_growth(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
    ) -> Optional[float]:
        """
        Computes forecast-based growth relative to trailing twelve-month profit.
        """

        income_df = api.get_ttm_income(stock, context.current_dt, periods=4)
        if income_df.empty or "net_profit" not in income_df:
            return None
        ttm_profit = float(income_df["net_profit"].sum())
        if ttm_profit <= 0:
            return None

        forecast_df = api.get_forecast(stock, context.current_dt)
        if forecast_df.empty or "forecast_net_profit" not in forecast_df:
            return None
        expected_profit = float(forecast_df["forecast_net_profit"].iloc[0])
        growth = (expected_profit - ttm_profit) / abs(ttm_profit)
        return max(min(growth, 1.0), -0.5)

    def calculate_net_profit_ttm_growth(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
    ) -> Optional[float]:
        """Computes realized TTM net profit growth versus the prior-year TTM."""

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

    def get_enhanced_financial_data(
        self,
        api: MarketDataApi,
        context: StrategyContextLike,
        stock: str,
    ) -> dict[str, float]:
        """Collects quality-related inputs from valuation, income, and balance data."""

        valuation_df = api.get_valuation(stock, context.current_dt)
        if valuation_df.empty or "market_cap" not in valuation_df:
            return {}
        market_cap = float(valuation_df["market_cap"].iloc[0])

        stat_year = (
            context.current_dt.year - 1 if context.current_dt.month < 5 else context.current_dt.year
        )
        income_df = api.get_income_statement(stock, stat_year)
        if income_df.empty:
            return {"market_cap": market_cap}

        revenue = float(income_df["operating_revenue"].iloc[0])
        cost = float(income_df["operating_cost"].iloc[0])
        gross_margin = (revenue - cost) / revenue if revenue > 0 else 0.0

        balance_df = api.get_balance_sheet(stock, stat_year)
        if balance_df.empty:
            debt_ratio = 0.5
        else:
            total_assets = float(balance_df["total_assets"].iloc[0])
            total_liability = float(balance_df["total_liability"].iloc[0])
            debt_ratio = total_liability / total_assets if total_assets > 0 else 0.5

        return {
            "gross_margin": gross_margin,
            "debt_ratio": debt_ratio,
            "market_cap": market_cap,
        }

    @staticmethod
    def _score_pe_ratio(pe_ratio: Optional[float], rule: FactorRule) -> float:
        if pe_ratio is None or pe_ratio <= 0:
            return 0.0
        if pe_ratio <= rule.optimal_range[1]:
            return rule.weight
        if pe_ratio <= 25:
            return rule.weight * 0.8
        if pe_ratio <= 30:
            return rule.weight * 0.6
        if pe_ratio <= 40:
            return rule.weight * 0.3
        return 0.0

    @staticmethod
    def _score_growth(growth: Optional[float], rule: FactorRule) -> float:
        if growth is None:
            return 0.0
        min_threshold = rule.min_threshold
        lower_optimal = rule.optimal_range[0]
        if growth < min_threshold:
            if growth < 0:
                return max(rule.weight * (growth / min_threshold), -5.0)
            return rule.weight * 0.5 * (growth / min_threshold)
        if growth >= lower_optimal:
            return rule.weight
        if growth >= 0.10:
            ratio = (growth - 0.10) / (lower_optimal - 0.10)
            return rule.weight * (0.5 + 0.5 * ratio)
        if growth >= 0.05:
            ratio = (growth - 0.05) / (0.10 - 0.05)
            return rule.weight * 0.5 * ratio
        return 0.0

    @staticmethod
    def _score_gross_margin(gross_margin: Optional[float], rule: FactorRule) -> float:
        if gross_margin is None:
            return 0.0
        if gross_margin < rule.min_threshold:
            return 0.0
        if gross_margin >= rule.optimal_range[0]:
            return rule.weight
        if gross_margin >= 0.20:
            ratio = (gross_margin - 0.20) / (rule.optimal_range[0] - 0.20)
            return rule.weight * (0.5 + 0.5 * ratio)
        if gross_margin >= 0.10:
            ratio = (gross_margin - 0.10) / (0.20 - 0.10)
            return rule.weight * 0.5 * ratio
        return 0.0

    @staticmethod
    def _score_debt_ratio(debt_ratio: Optional[float], rule: FactorRule) -> float:
        if debt_ratio is None:
            return 0.0
        optimal_upper = rule.optimal_range[1]
        if debt_ratio <= optimal_upper:
            return rule.weight
        if debt_ratio <= 0.60:
            ratio = 1 - (debt_ratio - optimal_upper) / (0.60 - optimal_upper)
            return rule.weight * (0.5 + 0.5 * ratio)
        if debt_ratio <= 0.70:
            ratio = 1 - (debt_ratio - 0.60) / (0.70 - 0.60)
            return rule.weight * 0.5 * ratio
        return 0.0

    @staticmethod
    def _score_market_cap(market_cap: Optional[float], rule: FactorRule) -> float:
        if market_cap is None:
            return 0.0
        low, high = rule.optimal_range
        acceptable_low, acceptable_high = rule.acceptable_range
        if low <= market_cap <= high:
            return rule.weight
        if acceptable_low <= market_cap < low or high < market_cap <= acceptable_high:
            return rule.weight * 0.5
        return 0.0
