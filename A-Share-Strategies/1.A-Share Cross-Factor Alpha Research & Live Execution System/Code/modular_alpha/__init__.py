"""
Modular package for the A-share cross-factor alpha strategy.

This package contains configuration, factor calculation, stock filtering,
portfolio construction, risk control, and execution bridge modules.
"""

from .execution_bridge import QmtExecutionBridge
from .fundamental_factors import FundamentalFactorLibrary
from .industry_overlay import IndustryOverlayEngine
from .portfolio_construction import PortfolioConstructionEngine
from .risk_controls import RiskControlEngine
from .stock_filters import StockFilterEngine
from .strategy_config import StrategyConfig, build_default_strategy_config
from .strategy_orchestrator import CrossFactorAlphaResearchStrategy
from .technical_factors import TechnicalFactorLibrary

__all__ = [
    "CrossFactorAlphaResearchStrategy",
    "FundamentalFactorLibrary",
    "IndustryOverlayEngine",
    "PortfolioConstructionEngine",
    "QmtExecutionBridge",
    "RiskControlEngine",
    "StockFilterEngine",
    "StrategyConfig",
    "TechnicalFactorLibrary",
    "build_default_strategy_config",
]
