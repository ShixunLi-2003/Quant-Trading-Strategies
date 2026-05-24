"""Compute portfolio statistics from the simulated equity curve."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def _to_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _max_streak(condition: pd.Series) -> int:
    groups = [len(list(v)) for k, v in itertools.groupby(np.where(condition, 1, np.nan)) if k == 1]
    return max(groups) if groups else 0


def strategy_evaluate(equity: pd.DataFrame, net_col: str = "nav", pct_col: str = "return"):
    """Summarize return, drawdown, consistency, and periodic performance."""
    results = pd.DataFrame(columns=["value"])

    results.loc["cumulative_nav", "value"] = round(float(equity[net_col].iloc[-1]), 4)

    elapsed_days = (equity["candle_begin_time"].iloc[-1] - equity["candle_begin_time"].iloc[0]).total_seconds() / 86400
    annual_return = equity[net_col].iloc[-1] ** (365 / elapsed_days) - 1 if elapsed_days > 0 else 0.0
    results.loc["annual_return", "value"] = _to_pct(annual_return)

    equity["nav_peak"] = equity[net_col].cummax()
    equity["drawdown"] = equity[net_col] / equity["nav_peak"] - 1
    end_date = equity.loc[equity["drawdown"].idxmin(), "candle_begin_time"]
    max_drawdown = float(equity["drawdown"].min())
    start_date = equity.loc[equity["candle_begin_time"] <= end_date].sort_values(net_col, ascending=False).iloc[0]["candle_begin_time"]

    results.loc["max_drawdown", "value"] = _to_pct(max_drawdown)
    results.loc["max_drawdown_start", "value"] = str(start_date)
    results.loc["max_drawdown_end", "value"] = str(end_date)
    results.loc["calmar_ratio", "value"] = round(annual_return / abs(max_drawdown), 4) if max_drawdown != 0 else np.nan

    winning_periods = int((equity[pct_col] > 0).sum())
    losing_periods = int((equity[pct_col] <= 0).sum())
    results.loc["winning_periods", "value"] = winning_periods
    results.loc["losing_periods", "value"] = losing_periods
    results.loc["win_rate", "value"] = _to_pct(winning_periods / len(equity)) if len(equity) else "0.00%"
    results.loc["average_period_return", "value"] = _to_pct(float(equity[pct_col].mean()))

    avg_win = equity.loc[equity[pct_col] > 0, pct_col].mean()
    avg_loss = equity.loc[equity[pct_col] <= 0, pct_col].mean()
    payoff_ratio = float(avg_win / -avg_loss) if pd.notna(avg_win) and pd.notna(avg_loss) and avg_loss != 0 else np.nan
    if equity["liquidated"].eq(1).any():
        payoff_ratio = 0.0
    results.loc["payoff_ratio", "value"] = round(payoff_ratio, 4) if pd.notna(payoff_ratio) else np.nan

    results.loc["best_period_return", "value"] = _to_pct(float(equity[pct_col].max()))
    results.loc["worst_period_return", "value"] = _to_pct(float(equity[pct_col].min()))
    results.loc["longest_win_streak", "value"] = _max_streak(equity[pct_col] > 0)
    results.loc["longest_loss_streak", "value"] = _max_streak(equity[pct_col] <= 0)
    results.loc["return_volatility", "value"] = _to_pct(float(equity[pct_col].std()))

    temp = equity.copy().set_index("candle_begin_time")
    year_return = temp[[pct_col]].resample("Y").apply(lambda x: (1 + x).prod() - 1)
    month_return = temp[[pct_col]].resample("M").apply(lambda x: (1 + x).prod() - 1)
    quarter_return = temp[[pct_col]].resample("Q").apply(lambda x: (1 + x).prod() - 1)

    for frame in (year_return, month_return, quarter_return):
        frame["return_pct"] = frame[pct_col].map(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else x)

    return results, year_return, month_return, quarter_return
