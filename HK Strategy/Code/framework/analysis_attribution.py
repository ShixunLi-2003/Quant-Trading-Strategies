"""
Contribution Attribution

Computes symbol-level return contribution based on realized portfolio weights.
"""

from __future__ import annotations

import pandas as pd


def compute_symbol_contribution(weights: pd.DataFrame, asset_returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    shifted_weights = weights.reindex(asset_returns.index).fillna(0.0).shift(1).fillna(0.0)
    contribution = shifted_weights * asset_returns.fillna(0.0)
    summary = pd.DataFrame(
        {
            "total_contribution": contribution.sum(),
            "avg_weight": weights.reindex(asset_returns.index).fillna(0.0).mean(),
            "turnover": weights.reindex(asset_returns.index).fillna(0.0).diff().abs().sum() / 2.0,
        }
    ).sort_values("total_contribution", ascending=False)
    return contribution, summary
