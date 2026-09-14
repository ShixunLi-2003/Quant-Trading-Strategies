from __future__ import annotations

import math

import numpy as np
import pandas as pd


def rank_ic(group: pd.DataFrame, factor: str, target: str) -> float:
    valid = group[[factor, target]].dropna()
    if len(valid) < 10:
        return np.nan
    return float(valid[factor].rank().corr(valid[target].rank()))


def daily_rank_ic(panel: pd.DataFrame, factor: str, target: str) -> pd.Series:
    values = {
        trade_date: rank_ic(group, factor, target)
        for trade_date, group in panel.groupby("trade_date", sort=True)
    }
    return pd.Series(values, dtype=float, name=factor).dropna().sort_index()


def newey_west_mean_test(values: pd.Series, max_lag: int = 3) -> dict[str, float | int]:
    sample = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    observations = int(sample.size)
    if observations < 2:
        return {
            "n_observations": observations,
            "mean": float(sample.mean()) if observations else np.nan,
            "standard_error": np.nan,
            "t_stat": np.nan,
            "p_value_normal": np.nan,
            "max_lag": int(max_lag),
        }

    sample_mean = float(sample.mean())
    demeaned = sample - sample_mean
    lag_limit = min(max(int(max_lag), 0), observations - 1)
    long_run_variance = float(np.dot(demeaned, demeaned) / observations)
    for lag in range(1, lag_limit + 1):
        covariance = float(np.dot(demeaned[lag:], demeaned[:-lag]) / observations)
        bartlett_weight = 1.0 - lag / (lag_limit + 1.0)
        long_run_variance += 2.0 * bartlett_weight * covariance

    long_run_variance = max(long_run_variance, 0.0)
    standard_error = math.sqrt(long_run_variance / observations)
    t_stat = sample_mean / standard_error if standard_error > 0 else np.nan
    p_value = math.erfc(abs(t_stat) / math.sqrt(2.0)) if np.isfinite(t_stat) else np.nan
    return {
        "n_observations": observations,
        "mean": sample_mean,
        "standard_error": standard_error,
        "t_stat": float(t_stat),
        "p_value_normal": float(p_value),
        "max_lag": lag_limit,
    }


def factor_ic_summary(panel: pd.DataFrame, factors: list[str], target: str) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for factor in factors:
        daily_ic = daily_rank_ic(panel, factor, target)
        standard_deviation = float(daily_ic.std()) if len(daily_ic) > 1 else np.nan
        rows.append(
            {
                "factor": factor,
                "mean_ic": float(daily_ic.mean()),
                "ic_std": standard_deviation,
                "ic_ir": float(daily_ic.mean() / standard_deviation) if standard_deviation else np.nan,
                "positive_ic_ratio": float((daily_ic > 0).mean()),
                "n_days": int(len(daily_ic)),
            }
        )
    output = pd.DataFrame(rows)
    return output.sort_values("mean_ic", key=lambda values: values.abs(), ascending=False).reset_index(
        drop=True
    )


def factor_ic_robustness(
    panel: pd.DataFrame,
    factors: list[str],
    target: str,
    hac_lag: int = 3,
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for factor in factors:
        daily_ic = daily_rank_ic(panel, factor, target)
        standard_deviation = float(daily_ic.std(ddof=1)) if len(daily_ic) > 1 else np.nan
        naive_standard_error = standard_deviation / math.sqrt(len(daily_ic)) if len(daily_ic) > 1 else np.nan
        hac = newey_west_mean_test(daily_ic, hac_lag)
        rows.append(
            {
                "factor": factor,
                "start_date": daily_ic.index.min() if not daily_ic.empty else pd.NaT,
                "end_date": daily_ic.index.max() if not daily_ic.empty else pd.NaT,
                "n_days": int(len(daily_ic)),
                "mean_ic": float(daily_ic.mean()) if not daily_ic.empty else np.nan,
                "ic_std": standard_deviation,
                "ic_ir_daily": float(daily_ic.mean() / standard_deviation)
                if np.isfinite(standard_deviation) and standard_deviation > 0
                else np.nan,
                "ic_ir_annualized": float(daily_ic.mean() / standard_deviation * math.sqrt(252.0))
                if np.isfinite(standard_deviation) and standard_deviation > 0
                else np.nan,
                "positive_ic_ratio": float((daily_ic > 0).mean()) if not daily_ic.empty else np.nan,
                "naive_t_stat": float(daily_ic.mean() / naive_standard_error)
                if np.isfinite(naive_standard_error) and naive_standard_error > 0
                else np.nan,
                "hac_lag": int(hac["max_lag"]),
                "hac_standard_error": float(hac["standard_error"]),
                "hac_t_stat": float(hac["t_stat"]),
                "hac_p_value_normal": float(hac["p_value_normal"]),
            }
        )
    return pd.DataFrame(rows).sort_values("mean_ic", key=lambda values: values.abs(), ascending=False)


def quantile_backtest(
    panel: pd.DataFrame,
    score_column: str,
    target_column: str,
    quantiles: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = panel[["trade_date", "stock_code", score_column, target_column]].dropna().copy()

    def assign(group: pd.Series) -> pd.Series:
        if len(group) < quantiles * 2:
            return pd.Series(index=group.index, dtype=float)
        return pd.qcut(group.rank(method="first"), quantiles, labels=False, duplicates="drop") + 1

    working["quantile"] = working.groupby("trade_date")[score_column].transform(assign)
    returns = working.dropna(subset=["quantile"]).pivot_table(
        index="trade_date",
        columns="quantile",
        values=target_column,
        aggfunc="mean",
    )
    returns.columns = [f"q{int(column)}" for column in returns.columns]
    if "q1" in returns and f"q{quantiles}" in returns:
        returns["long_short"] = returns[f"q{quantiles}"] - returns["q1"]
    nav = (1.0 + returns.fillna(0.0)).cumprod()
    return returns.reset_index(), nav.reset_index()
