from __future__ import annotations

import numpy as np
import pandas as pd


def compute_bbi(
    close: pd.DataFrame,
    windows: tuple[int, int, int, int] = (3, 6, 12, 24),
) -> pd.DataFrame:
    rolling_means = [close.rolling(window=window, min_periods=window).mean() for window in windows]
    return sum(rolling_means) / float(len(rolling_means))


def top_n_hold(
    factor: pd.DataFrame,
    top_n: int = 5,
    rebalance_freq: str = "M",
    ascending: bool = False,
    rebalance_every_n_days: int | None = None,
    entry_filter: pd.DataFrame | None = None,
    exit_filter: pd.DataFrame | None = None,
) -> pd.DataFrame:
    factor = factor.sort_index()
    weights = pd.DataFrame(0.0, index=factor.index, columns=factor.columns)
    entry_filter = (
        entry_filter.reindex(index=factor.index, columns=factor.columns).fillna(False).astype(bool)
        if entry_filter is not None
        else pd.DataFrame(True, index=factor.index, columns=factor.columns)
    )
    exit_filter = (
        exit_filter.reindex(index=factor.index, columns=factor.columns).fillna(False).astype(bool)
        if exit_filter is not None
        else pd.DataFrame(False, index=factor.index, columns=factor.columns)
    )

    if rebalance_every_n_days is not None:
        rebalance_dates = factor.index[:: int(rebalance_every_n_days)].tolist()
    else:
        rebalance_dates = factor.groupby(factor.index.to_period(rebalance_freq)).apply(lambda frame: frame.index[-1]).tolist()

    rebalance_date_set = set(rebalance_dates)
    current_selected: list[str] = []

    for date in factor.index:
        if current_selected:
            exited = exit_filter.loc[date, current_selected]
            current_selected = [symbol for symbol in current_selected if not bool(exited.get(symbol, False))]

        if date in rebalance_date_set:
            scores = factor.loc[date].dropna()
            if not scores.empty:
                eligible = entry_filter.loc[date]
                scores = scores[eligible.reindex(scores.index).fillna(False)]
            current_selected = scores.sort_values(ascending=ascending).head(top_n).index.tolist() if not scores.empty else []

        if current_selected:
            weights.loc[date, current_selected] = 1.0 / len(current_selected)

    return weights


def top_n_hold_dynamic(
    factor: pd.DataFrame,
    top_n_series: pd.Series,
    rebalance_freq: str = "M",
    ascending: bool = False,
    rebalance_every_n_days: int | None = None,
    entry_filter: pd.DataFrame | None = None,
    exit_filter: pd.DataFrame | None = None,
) -> pd.DataFrame:
    factor = factor.sort_index()
    weights = pd.DataFrame(0.0, index=factor.index, columns=factor.columns)
    top_n_series = pd.Series(top_n_series, index=factor.index).reindex(factor.index).ffill().bfill()
    entry_filter = (
        entry_filter.reindex(index=factor.index, columns=factor.columns).fillna(False).astype(bool)
        if entry_filter is not None
        else pd.DataFrame(True, index=factor.index, columns=factor.columns)
    )
    exit_filter = (
        exit_filter.reindex(index=factor.index, columns=factor.columns).fillna(False).astype(bool)
        if exit_filter is not None
        else pd.DataFrame(False, index=factor.index, columns=factor.columns)
    )

    if rebalance_every_n_days is not None:
        rebalance_dates = factor.index[:: int(rebalance_every_n_days)].tolist()
    else:
        rebalance_dates = factor.groupby(factor.index.to_period(rebalance_freq)).apply(lambda frame: frame.index[-1]).tolist()

    rebalance_date_set = set(rebalance_dates)
    current_selected: list[str] = []

    for date in factor.index:
        if current_selected:
            exited = exit_filter.loc[date, current_selected]
            current_selected = [symbol for symbol in current_selected if not bool(exited.get(symbol, False))]

        if date in rebalance_date_set:
            current_top_n = max(int(top_n_series.loc[date]), 0)
            scores = factor.loc[date].dropna()
            if not scores.empty:
                eligible = entry_filter.loc[date]
                scores = scores[eligible.reindex(scores.index).fillna(False)]
            current_selected = scores.sort_values(ascending=ascending).head(current_top_n).index.tolist() if current_top_n > 0 and not scores.empty else []

        if current_selected:
            weights.loc[date, current_selected] = 1.0 / len(current_selected)

    return weights


def factor_above_threshold(factor: pd.Series | pd.DataFrame, threshold: float = 0.0):
    return factor > threshold
