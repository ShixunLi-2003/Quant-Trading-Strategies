"""
Central configuration objects for the modular alpha strategy.

This file defines factor parameters, filter thresholds, portfolio settings,
risk limits, and execution settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FactorRule:
    """Generic rule definition for factor scoring."""

    weight: float
    optimal_range: tuple[float, float] | None = None
    acceptable_range: tuple[float, float] | None = None
    min_threshold: float | None = None
    max_threshold: float | None = None
    threshold: float | None = None


@dataclass(frozen=True)
class TechnicalConfig:
    """Configuration for technical factors and lookback windows."""

    rules: dict[str, FactorRule]
    momentum_window: int = 20
    volatility_window: int = 20
    volume_ratio_windows: tuple[int, int] = (5, 20)
    rsi_window: int = 14
    breakout_window: int = 10


@dataclass(frozen=True)
class FundamentalConfig:
    """Configuration for fundamental factors."""

    rules: dict[str, FactorRule]


@dataclass(frozen=True)
class FilterConfig:
    """Pre-trade stock filtering rules."""

    enable_rise_filter: bool = True
    short_rise_period: int = 120
    short_rise_threshold: float = 1.5
    long_rise_period: int = 720
    long_rise_threshold: float = 4.0
    enable_profit_drop_filter: bool = True
    profit_drop_threshold: float = -0.5


@dataclass(frozen=True)
class RiskConfig:
    """Position-level and portfolio-level risk limits."""

    stop_loss_threshold_1: float = 0.05
    stop_loss_threshold_2: float = 0.07
    take_profit_threshold_1: float = 0.20
    take_profit_threshold_2: float = 0.30
    max_drawdown_threshold: float = 0.06
    max_drawdown_reduce_ratio: float = 0.70
    max_drawdown_trigger_multiplier: float = 1.20


@dataclass(frozen=True)
class PortfolioConfig:
    """Portfolio construction and rebalance settings."""

    benchmark_code: str = "000300.XSHG"
    stock_num: int = 5
    rebalance_days_bull: int = 10
    rebalance_days_normal: int = 10
    rebalance_days_bear: int = 15
    max_position_per_stock: float = 0.20
    order_lot_size: int = 100
    order_diff_buffer_ratio: float = 0.10
    bear_market_buffer_multiplier: float = 1.50


@dataclass(frozen=True)
class ExecutionConfig:
    """External execution bridge settings."""

    order_url: str = "http://<YOUR_CLOUD_HOST_IP>:8080/order"
    http_timeout_seconds: int = 5
    buy_order_type: int = 23
    sell_order_type: int = 24


@dataclass(frozen=True)
class IndustryConfig:
    """Industry rotation, sector sentiment, and regional bonus settings."""

    enable_boom_check: bool = True
    boom_check_period: int = 20
    boom_pass_threshold: float = 0.0
    growth_industries: tuple[str, ...] = (
        "Lithium Battery",
        "New Energy",
        "Photovoltaic",
        "Chip",
        "Semiconductor",
        "Computing Power",
        "Artificial Intelligence",
        "Cloud Computing",
        "Biopharma",
        "Innovative Drug",
        "Optical Module",
    )
    value_industries: tuple[str, ...] = (
        "Bank",
        "Insurance",
        "Brokerage",
        "Coal",
        "Steel",
        "Nonferrous",
        "Building Materials",
    )
    cyclical_industries: tuple[str, ...] = (
        "Chemical",
        "Machinery",
        "Automobile",
        "Home Appliance",
        "Consumer Electronics",
        "Food and Beverage",
    )
    avoid_industries: tuple[str, ...] = ("Real Estate", "Tourism", "Agriculture")
    region_bonus: dict[str, float] = field(default_factory=lambda: {"Xinjiang": 5.0})
    bonus_scores: dict[str, float] = field(
        default_factory=lambda: {"growth": 8.0, "value": 3.0, "cyclical": 5.0}
    )
    boom_proxy_map: dict[str, str] = field(
        default_factory=lambda: {
            "Coal": "JM",
            "Chemical": "MA",
            "Steel": "RB",
            "Nonferrous": "CU",
            "Aluminum": "AL",
            "Crude Oil": "SC",
            "Artificial Intelligence": "801750.XSHG",
            "Computing Power": "801750.XSHG",
            "Chip": "801080.XSHG",
            "Semiconductor": "801080.XSHG",
            "New Energy": "801730.XSHG",
            "Photovoltaic": "801730.XSHG",
            "Lithium Battery": "801730.XSHG",
            "Innovative Drug": "801150.XSHG",
            "Biopharma": "801150.XSHG",
        }
    )


@dataclass(frozen=True)
class StrategyConfig:
    """Top-level strategy configuration."""

    technical: TechnicalConfig
    fundamental: FundamentalConfig
    filters: FilterConfig = field(default_factory=FilterConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    industry: IndustryConfig = field(default_factory=IndustryConfig)


def build_default_strategy_config() -> StrategyConfig:
    """Builds the default strategy configuration."""

    technical_rules = {
        "momentum": FactorRule(weight=8.0, optimal_range=(0.05, 0.15)),
        "volatility": FactorRule(weight=10.0, optimal_range=(0.10, 0.20)),
        "volume_ratio": FactorRule(weight=7.0, optimal_range=(1.0, 1.5)),
        "rsi": FactorRule(weight=7.0, optimal_range=(40.0, 60.0)),
        "breakout": FactorRule(weight=8.0, threshold=0.03),
    }
    fundamental_rules = {
        "pe_ratio": FactorRule(weight=12.0, optimal_range=(15.0, 20.0), max_threshold=30.0),
        "expected_growth": FactorRule(
            weight=10.0,
            optimal_range=(0.30, 1.0),
            min_threshold=0.05,
        ),
        "net_profit_ttm_growth": FactorRule(
            weight=10.0,
            optimal_range=(0.30, 1.0),
            min_threshold=0.05,
        ),
        "gross_margin": FactorRule(
            weight=10.0,
            optimal_range=(0.30, 0.50),
            min_threshold=0.10,
        ),
        "debt_ratio": FactorRule(
            weight=8.0,
            optimal_range=(0.20, 0.30),
            max_threshold=0.60,
        ),
        "market_cap": FactorRule(
            weight=10.0,
            optimal_range=(200.0, 500.0),
            acceptable_range=(100.0, 1000.0),
        ),
    }
    return StrategyConfig(
        technical=TechnicalConfig(rules=technical_rules),
        fundamental=FundamentalConfig(rules=fundamental_rules),
    )
