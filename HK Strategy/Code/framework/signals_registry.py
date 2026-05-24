"""
Signal Registry

Registers cross-sectional and timing signals so that strategy configurations can call them by name.
"""

from __future__ import annotations

from hk_quant.signals.cross_sectional import compute_bbi, factor_above_threshold, top_n_hold, top_n_hold_dynamic
from hk_quant.signals.timing import (
    breakout_signal,
    equity_ma_timing_signal,
    index_ma_risk_signal,
    light_equity_ma_risk_signal,
    ma_cross_signal,
    sharpe_decay_timing_signal,
)

CROSS_SECTIONAL_SIGNAL_REGISTRY = {
    "top_n_hold": top_n_hold,
    "top_n_hold_dynamic": top_n_hold_dynamic,
}

TIMING_SIGNAL_REGISTRY = {
    "ma_cross_signal": ma_cross_signal,
    "breakout_signal": breakout_signal,
    "factor_above_threshold": factor_above_threshold,
    "equity_ma_timing_signal": equity_ma_timing_signal,
    "light_equity_ma_risk_signal": light_equity_ma_risk_signal,
    "index_ma_risk_signal": index_ma_risk_signal,
    "sharpe_decay_timing_signal": sharpe_decay_timing_signal,
}


def build_cross_sectional_signal(name: str, factor, params: dict | None = None):
    params = params or {}
    if name not in CROSS_SECTIONAL_SIGNAL_REGISTRY:
        raise KeyError(f"Cross-sectional signal '{name}' is not registered.")
    return CROSS_SECTIONAL_SIGNAL_REGISTRY[name](factor, **params)


def build_timing_signal(name: str, data, params: dict | None = None):
    params = params or {}
    if name not in TIMING_SIGNAL_REGISTRY:
        raise KeyError(f"Timing signal '{name}' is not registered.")
    return TIMING_SIGNAL_REGISTRY[name](data, **params)
