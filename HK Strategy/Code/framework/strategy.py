"""
Composite Factor Construction

Normalizes factor weights and builds the composite cross-sectional ranking signal used by the strategy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from hk_quant.factors.registry import compute_factor


@dataclass
class FactorSpec:
    name: str
    ascending: bool
    params: tuple | list | dict | int | float | str | None
    weight: float


def normalize_factor_specs(raw_specs: list[dict]) -> list[FactorSpec]:
    specs = [
        FactorSpec(
            name=item["name"],
            ascending=bool(item["ascending"]),
            params=item.get("params"),
            weight=float(item.get("weight", 1.0)),
        )
        for item in raw_specs
    ]
    total_weight = sum(spec.weight for spec in specs)
    if total_weight <= 0:
        raise ValueError("Total factor weight must be positive.")
    for spec in specs:
        spec.weight = spec.weight / total_weight
    return specs


def compute_composite_factor(
    market_data: dict[str, pd.DataFrame],
    factor_specs: list[FactorSpec],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    component_factors: dict[str, pd.DataFrame] = {}
    component_ranks: dict[str, pd.DataFrame] = {}
    composite = None

    for spec in factor_specs:
        factor = compute_factor(spec.name, market_data=market_data, params=spec.params)
        rank = factor.rank(axis=1, ascending=spec.ascending, method="min")
        weighted_rank = rank * spec.weight
        component_factors[spec.name] = factor
        component_ranks[spec.name] = rank
        composite = weighted_rank if composite is None else composite.add(weighted_rank, fill_value=np.nan)

    if composite is None:
        raise ValueError("No factor specs were provided.")
    return composite, component_factors, component_ranks
