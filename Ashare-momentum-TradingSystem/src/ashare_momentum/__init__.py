"""A-share short-horizon research and execution components."""

from .backtest import CostModel, periodic_top_n_backtest
from .execution import PositionOwnership
from .factors import FACTOR_COLUMNS, build_factor_panel
from .risk import build_etf_exposure_schedule
from .validation import (
    daily_rank_ic,
    factor_ic_robustness,
    factor_ic_summary,
    newey_west_mean_test,
    quantile_backtest,
)

__all__ = [
    "CostModel",
    "FACTOR_COLUMNS",
    "PositionOwnership",
    "build_etf_exposure_schedule",
    "build_factor_panel",
    "daily_rank_ic",
    "factor_ic_robustness",
    "factor_ic_summary",
    "newey_west_mean_test",
    "periodic_top_n_backtest",
    "quantile_backtest",
]
