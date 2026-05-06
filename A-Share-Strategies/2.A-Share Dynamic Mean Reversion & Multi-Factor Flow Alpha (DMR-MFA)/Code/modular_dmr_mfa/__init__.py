"""
Modular package for the Dynamic Mean Reversion & Multi-Factor Flow Alpha strategy.

The package separates configuration, runtime state, technical diagnostics,
portfolio construction, and risk controls so that each trading stage can be
reviewed in isolation while preserving the original decision path.
"""

from .portfolio_construction import PortfolioConstructionEngine
from .risk_controls import RiskControlEngine
from .strategy_config import StrategyConfig, build_default_strategy_config
from .strategy_orchestrator import DynamicMeanReversionFlowAlphaStrategy
from .strategy_types import StrategyRuntimeState, TargetValueOrder
from .technical_factors import TechnicalFactorLibrary

__all__ = [
    "DynamicMeanReversionFlowAlphaStrategy",
    "PortfolioConstructionEngine",
    "RiskControlEngine",
    "StrategyConfig",
    "StrategyRuntimeState",
    "TargetValueOrder",
    "TechnicalFactorLibrary",
    "build_default_strategy_config",
]
