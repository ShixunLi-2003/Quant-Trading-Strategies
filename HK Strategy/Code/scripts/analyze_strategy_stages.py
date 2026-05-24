"""
Stage Analysis Runner

Analyzes strategy performance by calendar year and benchmark-defined market regime.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_quant.analysis.performance import calculate_performance_metrics
from hk_quant.config import ensure_directory, load_project_and_job_config
from hk_quant.data.loaders import load_benchmark_series


def regime_labels(benchmark: pd.Series, ma_window: int = 120) -> pd.Series:
    ma = benchmark.rolling(ma_window, min_periods=ma_window).mean()
    distance = benchmark / ma - 1.0
    label = pd.Series("unknown", index=benchmark.index)
    label.loc[distance >= 0.03] = "bull_above_ma"
    label.loc[(distance > -0.03) & (distance < 0.03)] = "sideways_near_ma"
    label.loc[distance <= -0.03] = "bear_below_ma"
    return label


def segment_metrics(returns: pd.Series, equity: pd.Series, mask: pd.Series) -> dict | None:
    seg_returns = returns.where(mask).dropna()
    if seg_returns.empty:
        return None
    seg_equity = (1.0 + seg_returns).cumprod()
    metrics = calculate_performance_metrics(seg_returns, equity_curve=seg_equity)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze strategy performance by year and benchmark regime.")
    parser.add_argument("--config", default="configs/vectorbt_w42_bear_defense_recommended.json")
    parser.add_argument("--output-subdir", default="analysis/strategy_stage_analysis")
    args = parser.parse_args()

    project_config, strategy_config = load_project_and_job_config(ROOT / args.config)
    output_dir = ensure_directory(ROOT / "outputs" / args.output_subdir)

    strategy_output = ROOT / "outputs" / strategy_config["output"]["subdir"]
    returns = pd.read_csv(strategy_output / "returns.csv", index_col=0).iloc[:, 0]
    returns.index = pd.to_datetime(returns.index)
    equity = pd.read_csv(strategy_output / "equity_curve.csv", index_col=0).iloc[:, 0]
    equity.index = pd.to_datetime(equity.index)

    benchmark = load_benchmark_series(project_config, strategy_config.get("benchmark"), start=strategy_config["date_range"]["start"], end=strategy_config["date_range"]["end"])
    benchmark = benchmark.reindex(returns.index).ffill()
    regime = regime_labels(benchmark)

    annual_rows = []
    for year, year_returns in returns.groupby(returns.index.year):
        if year_returns.empty:
            continue
        year_equity = (1.0 + year_returns).cumprod()
        metrics = calculate_performance_metrics(year_returns, equity_curve=year_equity)
        annual_rows.append({"year": int(year)} | metrics)
    annual_df = pd.DataFrame(annual_rows)
    annual_df.to_csv(output_dir / "annual_metrics.csv", index=False)

    regime_rows = []
    for label in sorted(regime.unique()):
        mask = regime == label
        metrics = segment_metrics(returns, equity, mask)
        if metrics:
            regime_rows.append({"regime": label, "days": int(mask.sum())} | metrics)
    regime_df = pd.DataFrame(regime_rows)
    regime_df.to_csv(output_dir / "regime_metrics.csv", index=False)

    monthly = returns.resample("M").apply(lambda x: (1.0 + x).prod() - 1.0).to_frame("strategy_return")
    benchmark_monthly = benchmark.pct_change().resample("M").apply(lambda x: (1.0 + x).prod() - 1.0).rename("benchmark_return")
    monthly["benchmark_return"] = benchmark_monthly
    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month
    monthly.to_csv(output_dir / "monthly_returns.csv")

    summary = {
        "best_year_by_return": annual_df.sort_values("annual_return", ascending=False).iloc[0].to_dict() if not annual_df.empty else None,
        "worst_year_by_return": annual_df.sort_values("annual_return", ascending=True).iloc[0].to_dict() if not annual_df.empty else None,
        "best_regime_by_sharpe": regime_df.sort_values("sharpe", ascending=False).iloc[0].to_dict() if not regime_df.empty else None,
        "worst_regime_by_sharpe": regime_df.sort_values("sharpe", ascending=True).iloc[0].to_dict() if not regime_df.empty else None,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print(f"Stage analysis exported to {output_dir}")


if __name__ == "__main__":
    main()
