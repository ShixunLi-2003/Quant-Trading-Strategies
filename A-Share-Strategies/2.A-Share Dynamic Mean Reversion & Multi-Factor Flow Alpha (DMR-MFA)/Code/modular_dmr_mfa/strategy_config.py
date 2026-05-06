"""
Configuration layer for the Dynamic Mean Reversion & Multi-Factor Flow Alpha strategy.

This module centralizes the benchmark setup, regime thresholds, stock pool,
entry signal parameters, and exit limits used throughout the trading cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BacktestConfig:
    """Execution environment settings applied during initialization."""

    benchmark_code: str = "000300.XSHG"
    use_real_price: bool = True
    fixed_slippage: float = 0.002
    open_tax: float = 0.0
    close_tax: float = 0.001
    open_commission: float = 0.0003
    close_commission: float = 0.0003
    min_commission: float = 5.0


@dataclass(frozen=True)
class RegimeConfig:
    """Benchmark Bollinger regime settings and position-capacity controls."""

    base_stock_num: int = 5
    max_stock_num: int = 7
    min_stock_num: int = 3
    bollinger_period: int = 20
    bollinger_std_multiplier: float = 2.0


@dataclass(frozen=True)
class SignalConfig:
    """Alpha signal settings for the oversold rebound and money-flow filter."""

    lookback_days: int = 10
    drop_days: int = 3
    drop_threshold: float = -0.07
    stock_pool: tuple[str, ...] = field(
        default_factory=lambda: (
            "601117.XSHG",
            "601600.XSHG",
            "601888.XSHG",
            "300274.XSHE",
            "300750.XSHE",
            "601919.XSHG",
            "002049.XSHE",
            "603881.XSHG",
            "002335.XSHE",
            "600089.XSHG",
            "002236.XSHE",
            "002056.XSHE",
            "300866.XSHE",
            "002611.XSHE",
            "600760.XSHG",
            "300693.XSHE",
            "002402.XSHE",
            "002600.XSHE",
            "300207.XSHE",
            "603486.XSHG",
            "000591.XSHE",
            "000027.XSHE",
            "600011.XSHG",
            "601899.XSHG",
            "603799.XSHG",
            "002340.XSHE",
            "002780.XSHE",
            "600160.XSHG",
            "601225.XSHG",
            "002555.XSHE",
            "600803.XSHG",
            "300059.XSHE",
            "002736.XSHE",
        )
    )


@dataclass(frozen=True)
class RiskConfig:
    """Position-level exit thresholds and technical confirmation settings."""

    take_profit_pct: float = 0.15
    stop_loss_pct: float = -0.035
    obv_profit_floor: float = 0.01
    bbi_drawdown_floor: float = -0.03


@dataclass(frozen=True)
class StrategyConfig:
    """Top-level configuration bundle for the strategy."""

    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)


def build_default_strategy_config() -> StrategyConfig:
    """Builds the default configuration used by the modular strategy package."""

    return StrategyConfig()
