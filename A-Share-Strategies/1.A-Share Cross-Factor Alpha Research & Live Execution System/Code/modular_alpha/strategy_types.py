"""
Shared types and interfaces for the modular alpha package.

This file defines runtime state objects, order objects, and data access
interfaces used across the strategy modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Protocol

import pandas as pd


@dataclass
class DynamicWeightState:
    """Tracks regime-dependent factor multipliers and rebalance cadence."""

    market_status: str = "normal"
    tech_weight_multiplier: float = 1.0
    fundamental_weight_multiplier: float = 1.0
    rebalance_days: int = 10


@dataclass
class StrategyRuntimeState:
    """Mutable runtime state used across trading days."""

    trading_day_counter: int = 0
    portfolio_high: float = 0.0
    last_portfolio_value: Optional[float] = None
    dynamic_weight: DynamicWeightState = field(default_factory=DynamicWeightState)


@dataclass
class TargetOrder:
    """Normalized target order used across rebalance and risk modules."""

    security: str
    target_value: Optional[float] = None
    target_shares: Optional[int] = None
    delta_shares: int = 0
    reason: str = ""


@dataclass
class TradeSignal:
    """Transport-level trade message for the external execution bridge."""

    security: str
    is_buy: bool
    quantity: int
    price: float
    reason: str = ""


@dataclass
class FactorScoreCard:
    """Single-stock scoring result used for ranking and diagnostics."""

    stock: str
    total_score: float
    component_scores: dict[str, float]


class CurrentQuoteLike(Protocol):
    """Minimal shape required from a current quote object."""

    paused: bool
    last_price: float


class SecurityInfoLike(Protocol):
    """Minimal shape required from a security metadata object."""

    name: str
    display_name: str


class PositionLike(Protocol):
    """Minimal shape required from a live position object."""

    avg_cost: float
    total_amount: int
    value: float


class PortfolioLike(Protocol):
    """Minimal shape required from a portfolio snapshot."""

    total_value: float
    positions: Mapping[str, PositionLike]


class StrategyContextLike(Protocol):
    """Minimal runtime context needed by the modular strategy."""

    current_dt: datetime
    portfolio: PortfolioLike


class MarketDataApi(Protocol):
    """
    Data interface used by factor, filter, and portfolio modules.
    """

    def get_index_stocks(self, index_code: str, date: datetime) -> list[str]:
        ...

    def get_current_data(self) -> Mapping[str, CurrentQuoteLike]:
        ...

    def get_security_info(self, stock: str) -> SecurityInfoLike:
        ...

    def get_industry(self, stock: str, date: datetime) -> Mapping[str, dict[str, Any]]:
        ...

    def get_dominant_future(self, symbol: str) -> Optional[str]:
        ...

    def get_price(
        self,
        security: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str,
        fields: list[str],
        skip_paused: bool = False,
        fq: Optional[str] = None,
    ) -> pd.DataFrame:
        ...

    def get_ttm_income(
        self,
        stock: str,
        as_of_date: datetime,
        periods: int = 4,
    ) -> pd.DataFrame:
        ...

    def get_valuation(self, stock: str, as_of_date: datetime) -> pd.DataFrame:
        ...

    def get_forecast(self, stock: str, as_of_date: datetime) -> pd.DataFrame:
        ...

    def get_income_statement(self, stock: str, stat_year: int) -> pd.DataFrame:
        ...

    def get_balance_sheet(self, stock: str, stat_year: int) -> pd.DataFrame:
        ...
