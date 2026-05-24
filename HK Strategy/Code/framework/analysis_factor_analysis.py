"""
Factor Evaluation

Computes forward returns, information coefficients, and quantile portfolio results for factor research.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_forward_returns(close: pd.DataFrame, periods: list[int]) -> dict[int, pd.DataFrame]:
    return {period: close.pct_change(period, fill_method=None).shift(-period) for period in periods}


def compute_information_coefficient(
    factor: pd.DataFrame,
    forward_returns: dict[int, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ic_series = {}
    for period, forward_return in forward_returns.items():
        factor_rank = factor.rank(axis=1, method="average", pct=True)
        forward_rank = forward_return.rank(axis=1, method="average", pct=True)
        ic = factor_rank.corrwith(forward_rank, axis=1)
        ic_series[f"ic_{period}d"] = ic
    ic_frame = pd.DataFrame(ic_series)
    summary = pd.DataFrame(
        {
            "mean": ic_frame.mean(),
            "std": ic_frame.std(),
            "ir": ic_frame.mean() / ic_frame.std(),
        }
    )
    return ic_frame, summary


def compute_quantile_returns(
    factor: pd.DataFrame,
    forward_return: pd.DataFrame,
    quantiles: int = 5,
) -> tuple[pd.DataFrame, pd.Series]:
    pct_rank = factor.rank(axis=1, method="first", pct=True)
    quantile_labels = np.ceil(pct_rank * quantiles).clip(lower=1, upper=quantiles) if not pct_rank.empty else pct_rank
    quantile_return = pd.DataFrame(index=factor.index)
    for bucket in range(1, quantiles + 1):
        mask = quantile_labels == bucket
        quantile_return[f"q{bucket}"] = forward_return.where(mask).mean(axis=1)
    summary = quantile_return.mean()
    return quantile_return, summary


def compute_factor_analysis(
    factor: pd.DataFrame,
    close: pd.DataFrame,
    forward_periods: list[int],
    quantiles: int,
) -> dict[str, object]:
    forward_returns = compute_forward_returns(close, periods=forward_periods)
    ic_frame, ic_summary = compute_information_coefficient(factor, forward_returns)
    quantile_frames = {}
    quantile_summary = {}
    for period, forward_return in forward_returns.items():
        q_frame, q_summary = compute_quantile_returns(factor, forward_return, quantiles=quantiles)
        quantile_frames[period] = q_frame
        quantile_summary[period] = q_summary
    coverage = factor.notna().mean(axis=1).mean()
    factor_summary = {
        "coverage": float(coverage),
        "mean": float(factor.stack().mean()),
        "std": float(factor.stack().std()),
    }
    return {
        "forward_returns": forward_returns,
        "ic_frame": ic_frame,
        "ic_summary": ic_summary,
        "quantile_frames": quantile_frames,
        "quantile_summary": quantile_summary,
        "factor_summary": factor_summary,
    }
