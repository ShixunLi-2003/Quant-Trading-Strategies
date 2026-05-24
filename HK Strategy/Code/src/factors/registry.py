from __future__ import annotations

from hk_quant.factors.momentum import (
    avg_amount_level,
    bbi_upturn_score,
    obv_bottom_rising_score,
    obv_turn_volume_rebound_score,
    amount_zscore,
    price_level,
    price_vs_ma,
    relative_strength_vs_index,
    realized_volatility,
    breakout_confirmation_score,
    returns_momentum,
    trend_compression_score,
    volatility_compression_score,
    volume_dryup_rebound_score,
)
from hk_quant.factors.worldquant import w_22, w_24, w_42

FACTOR_REGISTRY = {
    "returns_momentum": returns_momentum,
    "price_vs_ma": price_vs_ma,
    "bbi_upturn_score": bbi_upturn_score,
    "obv_bottom_rising_score": obv_bottom_rising_score,
    "obv_turn_volume_rebound_score": obv_turn_volume_rebound_score,
    "volatility_compression_score": volatility_compression_score,
    "volume_dryup_rebound_score": volume_dryup_rebound_score,
    "relative_strength_vs_index": relative_strength_vs_index,
    "breakout_confirmation_score": breakout_confirmation_score,
    "price_level": price_level,
    "avg_amount_level": avg_amount_level,
    "amount_zscore": amount_zscore,
    "realized_volatility": realized_volatility,
    "trend_compression_score": trend_compression_score,
    "W-22": w_22,
    "W-24": w_24,
    "W-42": w_42,
}


def compute_factor(name: str, market_data: dict, params: dict | None = None):
    params = params or {}
    if name not in FACTOR_REGISTRY:
        raise KeyError(f"Factor '{name}' is not registered.")
    if isinstance(params, dict):
        return FACTOR_REGISTRY[name](market_data, **params)
    if isinstance(params, (list, tuple)):
        return FACTOR_REGISTRY[name](market_data, *params)
    return FACTOR_REGISTRY[name](market_data, params)
