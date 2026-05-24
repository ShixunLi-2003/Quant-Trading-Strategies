"""
Bear Overlay Search

Runs a narrow search over bear-market exposure and liquidity thresholds for the regime-control overlay.
"""

from __future__ import annotations

import argparse
import csv
import sys
from itertools import product
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_quant.analysis.performance import calculate_performance_metrics
from hk_quant.backtests.hk_execution import build_execution_config, simulate_target_weights
from hk_quant.backtests.vectorbt_engine import build_universe_mask
from hk_quant.config import ensure_directory, load_project_and_job_config, write_json
from hk_quant.data.loaders import load_benchmark_series, load_market_data, resolve_universe_symbols
from hk_quant.signals.registry import build_cross_sectional_signal
from hk_quant.strategy import compute_composite_factor, normalize_factor_specs


def frange(start: float, stop: float, step: float) -> list[float]:
    values = []
    current = start
    epsilon = step / 10
    while current <= stop + epsilon:
        values.append(round(current, 6))
        current += step
    return values


def build_bear_mask(benchmark: pd.Series, window: int, index: pd.Index) -> pd.Series:
    benchmark = benchmark.reindex(index).ffill().bfill()
    moving_average = benchmark.rolling(window, min_periods=window).mean()
    return (benchmark < moving_average).reindex(index).fillna(False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Narrow sweep for bear-defense overlay.")
    parser.add_argument("--config", default="configs/vectorbt_w42_bear_defense_recommended.json")
    parser.add_argument("--ma-window", type=int, default=120)
    parser.add_argument("--exposure-start", type=float, default=0.75)
    parser.add_argument("--exposure-end", type=float, default=0.9)
    parser.add_argument("--exposure-step", type=float, default=0.05)
    parser.add_argument("--bear-amounts", default="3000000,4000000,5000000")
    parser.add_argument("--output-subdir", default="optimizations/bear_defense_narrow")
    parser.add_argument("--save-every", type=int, default=3)
    args = parser.parse_args()

    project_config, strategy_config = load_project_and_job_config(ROOT / args.config)
    start = strategy_config["date_range"]["start"]
    end = strategy_config["date_range"]["end"]
    symbols = resolve_universe_symbols(strategy_config["universe"], project_config)
    market_data = load_market_data(
        symbols=symbols,
        fields=strategy_config.get("fields", ["open", "high", "close", "volume", "amount"]),
        project_config=project_config,
        start=start,
        end=end,
    )
    open_price = market_data["open"]
    close = market_data["close"]
    volume = market_data["volume"]
    amount = market_data["amount"]

    factor_specs = normalize_factor_specs(strategy_config["factor_list"])
    factor, _, _ = compute_composite_factor(market_data, factor_specs)
    universe_mask = build_universe_mask(strategy_config, market_data)
    if universe_mask is not None:
        factor = factor.where(universe_mask)

    base_signal_params = dict(strategy_config["signal"].get("params", {}))
    base_top_n = int(base_signal_params.get("top_n", 5))
    base_signal_params.pop("top_n", None)

    benchmark = load_benchmark_series(project_config, strategy_config.get("benchmark"), start=start, end=end)
    bear_mask = build_bear_mask(benchmark, args.ma_window, close.index)
    benchmark = benchmark.reindex(close.index).ffill().bfill()
    execution_config = build_execution_config(strategy_config)
    initial_cash = strategy_config["backtest"].get("initial_cash", 1_000_000)

    bull_min_amount = float(strategy_config.get("execution", {}).get("min_daily_amount_hkd", 2_000_000))
    exposure_values = frange(args.exposure_start, args.exposure_end, args.exposure_step)
    bear_amount_values = [float(item.strip()) for item in args.bear_amounts.split(",") if item.strip()]

    results = []
    output_root = ensure_directory(ROOT / "outputs" / args.output_subdir)
    csv_path = output_root / "all_results.csv"
    json_path = output_root / "top_results.json"
    total_runs = len(exposure_values) * len(bear_amount_values)

    for run_idx, (bear_exposure, bear_min_amount) in enumerate(product(exposure_values, bear_amount_values), start=1):
        dynamic_min_amount = pd.Series(bull_min_amount, index=close.index, dtype=float)
        dynamic_min_amount.loc[bear_mask] = bear_min_amount
        entry_filter = amount.ge(dynamic_min_amount, axis=0)

        signal_params = dict(base_signal_params)
        signal_params["top_n_series"] = pd.Series(base_top_n, index=close.index, dtype=float)
        signal_params["entry_filter"] = entry_filter
        signal_name = "top_n_hold_dynamic"

        weights = build_cross_sectional_signal(
            signal_name,
            factor=factor,
            params=signal_params,
        ).reindex(close.index).fillna(0.0)

        exposure_series = pd.Series(1.0, index=close.index, dtype=float)
        exposure_series.loc[bear_mask] = bear_exposure
        weights = weights.mul(exposure_series, axis=0)

        sim = simulate_target_weights(
            open_price=open_price,
            close_price=close,
            volume=volume,
            amount=amount,
            target_weights=weights,
            initial_cash=initial_cash,
            execution_config=execution_config,
        )
        metrics = calculate_performance_metrics(sim.returns, equity_curve=sim.equity_curve)

        returns = sim.returns
        returns_2018 = returns[returns.index.year == 2018]
        metrics_2018 = calculate_performance_metrics(
            returns_2018,
            equity_curve=(1.0 + returns_2018).cumprod(),
        ) if not returns_2018.empty else {}

        bear_returns = returns.where(bear_mask).dropna()
        bear_metrics = calculate_performance_metrics(
            bear_returns,
            equity_curve=(1.0 + bear_returns).cumprod(),
        ) if not bear_returns.empty else {}

        row = {
            "bear_exposure": bear_exposure,
            "bear_min_amount_hkd": int(bear_min_amount),
            "total_return": metrics["total_return"],
            "annual_return": metrics["annual_return"],
            "annual_volatility": metrics["annual_volatility"],
            "sharpe": metrics["sharpe"],
            "max_drawdown": metrics["max_drawdown"],
            "calmar": metrics["calmar"],
            "win_rate": metrics["win_rate"],
            "annual_return_2018": metrics_2018.get("annual_return"),
            "max_drawdown_2018": metrics_2018.get("max_drawdown"),
            "bear_regime_annual_return": bear_metrics.get("annual_return"),
            "bear_regime_sharpe": bear_metrics.get("sharpe"),
            "trading_cost_hkd": float(sim.costs["trading_cost_hkd"].sum()),
            "trade_count": int(sim.costs["trade_count"].sum()),
        }
        results.append(row)
        print(
            f"[{run_idx}/{total_runs}] exposure={bear_exposure:.2f} amount={int(bear_min_amount)} "
            f"sharpe={row['sharpe']:.4f} annual={row['annual_return']:.4f} "
            f"2018={row['annual_return_2018']:.4f} bear={row['bear_regime_annual_return']:.4f}"
        )

        if len(results) % args.save_every == 0:
            results_sorted = sorted(
                results,
                key=lambda x: (
                    (x["sharpe"] or -999),
                    (x["annual_return"] or -999),
                    (x["annual_return_2018"] or -999),
                ),
                reverse=True,
            )
            with csv_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=list(results_sorted[0].keys()))
                writer.writeheader()
                writer.writerows(results_sorted)
            write_json({"top_results": results_sorted[:10]}, json_path)

    results_sorted = sorted(
        results,
        key=lambda x: (
            (x["sharpe"] or -999),
            (x["annual_return"] or -999),
            (x["annual_return_2018"] or -999),
        ),
        reverse=True,
    )
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results_sorted[0].keys()))
        writer.writeheader()
        writer.writerows(results_sorted)
    write_json({"top_results": results_sorted[:10]}, json_path)
    print(f"\nTop results written to {json_path}")


if __name__ == "__main__":
    main()
