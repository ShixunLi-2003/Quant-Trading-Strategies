from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_momentum.factors import FACTOR_COLUMNS, LOW_VOLATILITY_SIGNS, cross_sectional_zscore
from ashare_momentum.validation import factor_ic_robustness


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLES = ROOT / "results" / "tables"
TARGET_COLUMN = "fwd_ret_3d"
HORIZON = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build aggregate factor-robustness and matched-period benchmark evidence."
    )
    parser.add_argument("--factor-panel", type=Path, required=True)
    parser.add_argument("--strategy-periods", type=Path, required=True)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--train-end", default="2026-03-31")
    parser.add_argument(
        "--benchmark",
        action="append",
        default=[],
        metavar="LABEL=PARQUET_PATH",
        help="Repeat for each daily benchmark series. Only aggregate statistics are written.",
    )
    return parser.parse_args()


def signed_average(frame: pd.DataFrame, signs: dict[str, float]) -> pd.Series:
    columns = [f"z_{factor}" for factor in signs if f"z_{factor}" in frame.columns]
    weights = pd.Series({f"z_{factor}": float(signs[factor]) for factor in signs if f"z_{factor}" in frame})
    denominator = float(weights.abs().sum())
    return frame[columns].mul(weights, axis=1).sum(axis=1, skipna=True) / denominator


def add_composite_scores(panel: pd.DataFrame) -> pd.DataFrame:
    output = panel.copy()
    if not all(f"z_{factor}" in output for factor in FACTOR_COLUMNS):
        output = cross_sectional_zscore(output, FACTOR_COLUMNS)
    if "minute_momentum_score" not in output:
        output["minute_momentum_score"] = output[[f"z_{factor}" for factor in FACTOR_COLUMNS]].mean(axis=1)
    output["defensive_low_volatility_score"] = signed_average(output, LOW_VOLATILITY_SIGNS)
    output["tuned_blend_score"] = (
        0.4 * output["minute_momentum_score"] + 0.6 * output["defensive_low_volatility_score"]
    )
    return output


def write_factor_robustness(panel: pd.DataFrame, train_end: pd.Timestamp, tables: Path) -> None:
    score_columns = ["minute_momentum_score", "defensive_low_volatility_score", "tuned_blend_score"]
    splits = {
        "full": panel,
        "development": panel[panel["trade_date"] <= train_end],
        "holdout": panel[panel["trade_date"] > train_end],
    }
    rows = []
    for split, sample in splits.items():
        summary = factor_ic_robustness(sample, FACTOR_COLUMNS + score_columns, TARGET_COLUMN, hac_lag=HORIZON)
        summary.insert(0, "split", split)
        rows.append(summary)
    pd.concat(rows, ignore_index=True).to_csv(tables / "factor_ic_robustness.csv", index=False)


def assign_quantiles(values: pd.Series, quantiles: int = 5) -> pd.Series:
    if values.notna().sum() < quantiles * 2:
        return pd.Series(index=values.index, dtype=float)
    valid = values.dropna().rank(method="first")
    return pd.qcut(valid, quantiles, labels=False, duplicates="drop").add(1).reindex(values.index)


def spread_t_stat(values: pd.Series) -> float:
    sample = pd.to_numeric(values, errors="coerce").dropna()
    if len(sample) < 2 or sample.std(ddof=1) == 0:
        return np.nan
    return float(sample.mean() / (sample.std(ddof=1) / math.sqrt(len(sample))))


def non_overlapping_quantiles(
    panel: pd.DataFrame,
    score_column: str,
    split: str,
) -> pd.DataFrame:
    working = panel[["trade_date", score_column, TARGET_COLUMN]].dropna().copy()
    working["quantile"] = working.groupby("trade_date")[score_column].transform(assign_quantiles)
    daily = working.pivot_table(
        index="trade_date",
        columns="quantile",
        values=TARGET_COLUMN,
        aggfunc="mean",
    )
    daily.columns = [f"q{int(column)}" for column in daily.columns]
    daily = daily.sort_index()
    rows = []
    for offset in range(HORIZON):
        sleeve = daily.iloc[offset::HORIZON].copy()
        if not {"q1", "q2", "q3", "q4", "q5"}.issubset(sleeve.columns):
            continue
        sleeve["spread"] = sleeve["q5"] - sleeve["q1"]
        quantile_means = sleeve[["q1", "q2", "q3", "q4", "q5"]].mean()
        rows.append(
            {
                "score": score_column,
                "split": split,
                "offset": offset,
                "start_date": sleeve.index.min(),
                "end_date": sleeve.index.max(),
                "n_periods": int(len(sleeve)),
                **{f"{column}_mean_return": float(value) for column, value in quantile_means.items()},
                "q5_minus_q1_mean_return": float(sleeve["spread"].mean()),
                "q5_minus_q1_t_stat": spread_t_stat(sleeve["spread"]),
                "positive_spread_ratio": float((sleeve["spread"] > 0).mean()),
                "quantile_monotonicity": float(
                    pd.Series(range(1, 6), dtype=float).corr(quantile_means.reset_index(drop=True).rank())
                ),
                "q1_compound_return": float((1.0 + sleeve["q1"]).prod() - 1.0),
                "q5_compound_return": float((1.0 + sleeve["q5"]).prod() - 1.0),
            }
        )
    return pd.DataFrame(rows)


def write_non_overlapping_quantiles(panel: pd.DataFrame, train_end: pd.Timestamp, tables: Path) -> None:
    rows = []
    for split, sample in {
        "full": panel,
        "development": panel[panel["trade_date"] <= train_end],
        "holdout": panel[panel["trade_date"] > train_end],
    }.items():
        rows.append(non_overlapping_quantiles(sample, "tuned_blend_score", split))
    pd.concat(rows, ignore_index=True).to_csv(tables / "composite_nonoverlap_quantiles.csv", index=False)


def parse_benchmarks(values: list[str]) -> list[tuple[str, Path]]:
    parsed = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid benchmark specification: {value}")
        label, raw_path = value.split("=", 1)
        parsed.append((label.strip(), Path(raw_path.strip())))
    return parsed


def drawdown(nav: pd.Series) -> float:
    return float((nav / nav.cummax() - 1.0).min())


def annualized_return(total_return: float, start_date: pd.Timestamp, end_date: pd.Timestamp) -> float:
    elapsed_days = max((end_date - start_date).days, 1)
    return float((1.0 + total_return) ** (365.25 / elapsed_days) - 1.0)


def strategy_metrics(periods: pd.DataFrame) -> dict[str, object]:
    ordered = periods.sort_values("signal_date").copy()
    start_date = ordered["signal_date"].min()
    end_date = ordered["signal_date"].max()
    total_return = float(ordered["nav"].iloc[-1] - 1.0)
    returns = pd.to_numeric(ordered["account_return"], errors="coerce").dropna()
    volatility = float(returns.std(ddof=1) * math.sqrt(252.0 / HORIZON))
    sharpe = float(returns.mean() / returns.std(ddof=1) * math.sqrt(252.0 / HORIZON))
    return {
        "series": "Adaptive strategy",
        "series_type": "strategy",
        "start_date": start_date,
        "end_date": end_date,
        "observations": int(len(ordered)),
        "frequency": "three-session portfolio periods",
        "total_return": total_return,
        "annualized_return": annualized_return(total_return, start_date, end_date),
        "annualized_volatility": volatility,
        "sharpe_proxy_zero_rate": sharpe,
        "max_drawdown": drawdown(pd.concat([pd.Series([1.0]), ordered["nav"]], ignore_index=True)),
    }


def benchmark_metrics(
    label: str,
    path: Path,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, object]:
    frame = pd.read_parquet(path)
    date_column = "datetime" if "datetime" in frame else "trade_date"
    frame[date_column] = pd.to_datetime(frame[date_column]).dt.normalize()
    close = (
        frame.loc[frame[date_column].between(start_date, end_date), [date_column, "close"]]
        .dropna()
        .drop_duplicates(date_column, keep="last")
        .sort_values(date_column)
    )
    if len(close) < 2:
        raise ValueError(f"Benchmark {label} has fewer than two observations in the requested interval")
    daily_returns = close["close"].astype(float).pct_change().dropna()
    nav = close["close"].astype(float) / float(close["close"].iloc[0])
    total_return = float(nav.iloc[-1] - 1.0)
    volatility = float(daily_returns.std(ddof=1) * math.sqrt(252.0))
    sharpe = float(daily_returns.mean() / daily_returns.std(ddof=1) * math.sqrt(252.0))
    observed_start = pd.Timestamp(close[date_column].iloc[0])
    observed_end = pd.Timestamp(close[date_column].iloc[-1])
    return {
        "series": label,
        "series_type": "benchmark",
        "start_date": observed_start,
        "end_date": observed_end,
        "observations": int(len(close)),
        "frequency": "daily close",
        "total_return": total_return,
        "annualized_return": annualized_return(total_return, observed_start, observed_end),
        "annualized_volatility": volatility,
        "sharpe_proxy_zero_rate": sharpe,
        "max_drawdown": drawdown(nav),
    }


def write_benchmark_comparison(
    strategy_periods_path: Path,
    benchmarks: list[tuple[str, Path]],
    tables: Path,
) -> None:
    periods = pd.read_csv(strategy_periods_path)
    periods["signal_date"] = pd.to_datetime(periods["signal_date"]).dt.normalize()
    strategy = strategy_metrics(periods)
    rows = [strategy]
    for label, path in benchmarks:
        rows.append(benchmark_metrics(label, path, strategy["start_date"], strategy["end_date"]))
    comparison = pd.DataFrame(rows)
    comparison.to_csv(tables / "matched_period_benchmark_comparison.csv", index=False)

    benchmark_rows = comparison[comparison["series_type"] == "benchmark"]
    relative = benchmark_rows[["series", "start_date", "end_date", "total_return", "max_drawdown"]].copy()
    relative = relative.rename(
        columns={
            "series": "benchmark",
            "total_return": "benchmark_total_return",
            "max_drawdown": "benchmark_max_drawdown",
        }
    )
    relative.insert(0, "strategy", strategy["series"])
    relative["strategy_total_return"] = strategy["total_return"]
    relative["excess_total_return"] = strategy["total_return"] - relative["benchmark_total_return"]
    relative["strategy_max_drawdown"] = strategy["max_drawdown"]
    relative["drawdown_improvement"] = relative["strategy_max_drawdown"] - relative["benchmark_max_drawdown"]
    relative.to_csv(tables / "matched_period_excess_returns.csv", index=False)


def main() -> None:
    args = parse_args()
    args.tables.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(args.factor_panel)
    panel["trade_date"] = pd.to_datetime(panel["trade_date"]).dt.normalize()
    panel = add_composite_scores(panel)
    train_end = pd.Timestamp(args.train_end)
    write_factor_robustness(panel, train_end, args.tables)
    write_non_overlapping_quantiles(panel, train_end, args.tables)
    write_benchmark_comparison(args.strategy_periods, parse_benchmarks(args.benchmark), args.tables)


if __name__ == "__main__":
    main()
