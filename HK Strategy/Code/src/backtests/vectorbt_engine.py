from __future__ import annotations

from pathlib import Path

import pandas as pd

from hk_quant.analysis.attribution import compute_symbol_contribution
from hk_quant.analysis.performance import calculate_performance_metrics
from hk_quant.config import ensure_directory, write_json
from hk_quant.data.loaders import load_benchmark_series, load_market_data, resolve_universe_symbols
from hk_quant.backtests.hk_execution import build_execution_config, simulate_target_weights
from hk_quant.factors.registry import compute_factor
from hk_quant.signals.cross_sectional import compute_bbi
from hk_quant.signals.registry import build_cross_sectional_signal, build_timing_signal
from hk_quant.strategy import compute_composite_factor, normalize_factor_specs
from hk_quant.visualization.plots import plot_equity_curve


def resolve_output_dir(project_config: dict, subdir: str) -> Path:
    root = Path(project_config["_meta"]["base_dir"]).resolve()
    output_root = (root / project_config["output_root"]).resolve()
    return output_root / subdir


def build_universe_mask(strategy_config: dict, market_data: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    filter_config = strategy_config.get("universe_filter")
    if not filter_config:
        return None

    close = market_data["close"]
    amount = market_data["amount"]
    mask = pd.DataFrame(True, index=close.index, columns=close.columns)

    min_close = filter_config.get("min_close")
    if min_close is not None:
        mask &= close >= float(min_close)

    min_amount = filter_config.get("min_amount")
    if min_amount is not None:
        mask &= amount >= float(min_amount)

    max_price_rank_pct = filter_config.get("max_price_rank_pct")
    if max_price_rank_pct is not None:
        price_rank_pct = close.rank(axis=1, method="average", pct=True)
        mask &= price_rank_pct <= float(max_price_rank_pct)

    close_above_ma = filter_config.get("close_above_ma")
    if close_above_ma is not None:
        window = int(close_above_ma)
        moving_average = close.rolling(window, min_periods=window).mean()
        mask &= close > moving_average

    min_momentum = filter_config.get("min_momentum")
    if min_momentum is not None:
        momentum_window = int(filter_config.get("momentum_window", 20))
        momentum = close.pct_change(momentum_window, fill_method=None)
        mask &= momentum > float(min_momentum)

    positive_return_window = filter_config.get("positive_return_window")
    if positive_return_window is not None:
        positive_return = close.pct_change(int(positive_return_window), fill_method=None)
        mask &= positive_return > 0.0

    max_short_return = filter_config.get("max_short_return")
    if max_short_return is not None:
        short_return_window = int(filter_config.get("short_return_window", 3))
        short_return = close.pct_change(short_return_window, fill_method=None)
        mask &= short_return < float(max_short_return)

    return mask


def build_benchmark_bear_mask(
    benchmark_series: pd.Series | None,
    window: int,
    index: pd.Index,
) -> pd.Series | None:
    if benchmark_series is None:
        return None
    benchmark = benchmark_series.reindex(index).ffill().bfill()
    moving_average = benchmark.rolling(window, min_periods=window).mean()
    bear_mask = benchmark < moving_average
    return bear_mask.reindex(index).fillna(False)


def apply_timing_overlays(
    *,
    strategy_config: dict,
    weights: pd.DataFrame,
    open_price: pd.DataFrame,
    close_price: pd.DataFrame,
    volume: pd.DataFrame,
    amount: pd.DataFrame,
    execution_config: dict,
    initial_cash: float,
    benchmark_series: pd.Series | None,
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    timing_configs = strategy_config.get("timing_overlays", [])
    if not timing_configs:
        return weights, {}

    adjusted_weights = weights.copy()
    timing_signals: dict[str, pd.Series] = {}
    current_equity_curve = None

    for idx, timing_config in enumerate(timing_configs, start=1):
        if current_equity_curve is None:
            base_simulation = simulate_target_weights(
                open_price=open_price,
                close_price=close_price,
                volume=volume,
                amount=amount,
                target_weights=adjusted_weights,
                initial_cash=initial_cash,
                execution_config=execution_config,
            )
            current_equity_curve = base_simulation.equity_curve

        signal = build_timing_signal(
            timing_config["name"],
            data=(
                benchmark_series.reindex(adjusted_weights.index).ffill().bfill()
                if timing_config.get("source") == "benchmark" and benchmark_series is not None
                else current_equity_curve
            ),
            params=timing_config.get("params"),
        )
        signal_series = pd.Series(signal, index=adjusted_weights.index).astype(float).reindex(adjusted_weights.index).ffill().fillna(1.0)
        adjusted_weights = adjusted_weights.mul(signal_series, axis=0)
        timing_signals[timing_config.get("alias", f"timing_{idx}_{timing_config['name']}")] = signal_series

        simulation = simulate_target_weights(
            open_price=open_price,
            close_price=close_price,
            volume=volume,
            amount=amount,
            target_weights=adjusted_weights,
            initial_cash=initial_cash,
            execution_config=execution_config,
        )
        current_equity_curve = simulation.equity_curve

    return adjusted_weights, timing_signals


def run_vectorbt_strategy(project_config: dict, strategy_config: dict) -> dict[str, object]:
    start = strategy_config["date_range"]["start"]
    end = strategy_config["date_range"]["end"]
    symbols = resolve_universe_symbols(strategy_config["universe"], project_config)
    data_fields = strategy_config.get("fields", ["open", "close", "volume", "amount"])

    market_data = load_market_data(
        symbols=symbols,
        fields=data_fields,
        project_config=project_config,
        start=start,
        end=end,
    )
    open_price = market_data["open"]
    close = market_data["close"]
    volume = market_data["volume"]
    amount = market_data["amount"]
    benchmark_series = load_benchmark_series(project_config, strategy_config.get("benchmark"), start=start, end=end)
    factor_components = {}
    factor_ranks = {}
    if "factor_list" in strategy_config:
        factor_specs = normalize_factor_specs(strategy_config["factor_list"])
        factor, factor_components, factor_ranks = compute_composite_factor(market_data, factor_specs)
    else:
        factor = compute_factor(
            strategy_config["factor"]["name"],
            market_data=market_data,
            params=strategy_config["factor"].get("params"),
        )

    universe_mask = build_universe_mask(strategy_config, market_data)
    if universe_mask is not None:
        factor = factor.where(universe_mask)
        factor_components = {name: component.where(universe_mask) for name, component in factor_components.items()}
        factor_ranks = {name: rank.where(universe_mask) for name, rank in factor_ranks.items()}

    signal_params = dict(strategy_config["signal"].get("params", {}))
    regime_control = strategy_config.get("regime_risk_control", {})
    regime_outputs: dict[str, pd.Series] = {}
    if regime_control.get("enabled", False):
        bear_mask = build_benchmark_bear_mask(
            benchmark_series=benchmark_series,
            window=int(regime_control.get("benchmark_ma_window", 120)),
            index=close.index,
        )
        if bear_mask is not None:
            bull_top_n = int(regime_control.get("bull_top_n", signal_params.get("top_n", 5)))
            bear_top_n = int(regime_control.get("bear_top_n", max(1, bull_top_n - 2)))
            dynamic_top_n = pd.Series(bull_top_n, index=close.index, dtype=float)
            dynamic_top_n.loc[bear_mask] = bear_top_n
            signal_params["top_n_series"] = dynamic_top_n
            strategy_config["signal"]["name"] = "top_n_hold_dynamic"
            signal_params.pop("top_n", None)

            bull_min_amount = float(regime_control.get("bull_min_amount", 0.0))
            bear_min_amount = float(regime_control.get("bear_min_amount", bull_min_amount))
            dynamic_min_amount = pd.Series(bull_min_amount, index=close.index, dtype=float)
            dynamic_min_amount.loc[bear_mask] = bear_min_amount
            liquidity_entry_filter = amount.ge(dynamic_min_amount, axis=0)
            existing_entry_filter = signal_params.get("entry_filter")
            signal_params["entry_filter"] = (
                liquidity_entry_filter
                if existing_entry_filter is None
                else existing_entry_filter & liquidity_entry_filter
            )

            bull_exposure = float(regime_control.get("bull_exposure", 1.0))
            bear_exposure = float(regime_control.get("bear_exposure", bull_exposure))
            regime_exposure = pd.Series(bull_exposure, index=close.index, dtype=float)
            regime_exposure.loc[bear_mask] = bear_exposure
            regime_outputs["benchmark_bear_mask"] = bear_mask.astype(int)
            regime_outputs["dynamic_top_n"] = dynamic_top_n
            regime_outputs["dynamic_min_amount_hkd"] = dynamic_min_amount
            regime_outputs["regime_exposure"] = regime_exposure
        else:
            regime_exposure = pd.Series(1.0, index=close.index, dtype=float)
    else:
        regime_exposure = pd.Series(1.0, index=close.index, dtype=float)

    stock_timing_config = strategy_config.get("stock_timing", {})
    stock_timing_outputs: dict[str, pd.DataFrame] = {}
    if stock_timing_config.get("bbi_filter", {}).get("enabled", False):
        bbi_config = stock_timing_config["bbi_filter"]
        bbi_windows = tuple(int(window) for window in bbi_config.get("windows", [3, 6, 12, 24]))
        bbi = compute_bbi(close, windows=bbi_windows)
        bbi_slope = bbi.diff()
        if bbi_config.get("entry_enabled", True):
            entry_filter = bbi_slope > float(bbi_config.get("entry_min_slope", 0.0))
            signal_params["entry_filter"] = entry_filter
            stock_timing_outputs["bbi_entry_filter"] = entry_filter.astype(int)
        if bbi_config.get("exit_enabled", True):
            exit_filter = bbi_slope < float(bbi_config.get("exit_max_slope", 0.0))
            if bbi_config.get("exit_require_close_below_bbi", False):
                exit_filter &= close < bbi
            signal_params["exit_filter"] = exit_filter
            stock_timing_outputs["bbi_exit_filter"] = exit_filter.astype(int)
        stock_timing_outputs["bbi"] = bbi
        stock_timing_outputs["bbi_slope"] = bbi_slope

    weights = build_cross_sectional_signal(
        strategy_config["signal"]["name"],
        factor=factor,
        params=signal_params,
    ).reindex(close.index).fillna(0.0)
    weights = weights.mul(regime_exposure, axis=0)

    backtest_config = strategy_config["backtest"]
    execution_config = build_execution_config(strategy_config)
    timing_signals = {}
    weights, timing_signals = apply_timing_overlays(
        strategy_config=strategy_config,
        weights=weights,
        open_price=open_price,
        close_price=close,
        volume=volume,
        amount=amount,
        execution_config=execution_config,
        initial_cash=backtest_config.get("initial_cash", 1_000_000),
        benchmark_series=benchmark_series,
    )
    simulation = simulate_target_weights(
        open_price=open_price,
        close_price=close,
        volume=volume,
        amount=amount,
        target_weights=weights,
        initial_cash=backtest_config.get("initial_cash", 1_000_000),
        execution_config=execution_config,
    )
    equity_curve = simulation.equity_curve
    returns = simulation.returns
    metrics = calculate_performance_metrics(returns, equity_curve=equity_curve)
    metrics["trading_cost_hkd"] = float(simulation.costs["trading_cost_hkd"].sum())
    metrics["turnover_hkd"] = float(simulation.costs["turnover_hkd"].sum())
    metrics["trade_count"] = int(simulation.costs["trade_count"].sum())
    metrics["avg_daily_turnover_ratio"] = float(
        simulation.actual_weights.diff().abs().sum(axis=1).fillna(0.0).mean() / 2.0
    )

    benchmark_equity = None
    if benchmark_series is not None:
        benchmark_returns = benchmark_series.pct_change().fillna(0.0)
        benchmark_equity = (1.0 + benchmark_returns).cumprod() * backtest_config.get("initial_cash", 1_000_000)
        metrics["benchmark_total_return"] = float(benchmark_equity.iloc[-1] / benchmark_equity.iloc[0] - 1.0)

    asset_returns = close.pct_change(fill_method=None).fillna(0.0)
    contribution, contribution_summary = compute_symbol_contribution(simulation.actual_weights, asset_returns)

    output_dir = ensure_directory(
        resolve_output_dir(project_config, strategy_config["output"]["subdir"])
    )
    factor.to_csv(output_dir / "factor.csv")
    for name, component in factor_components.items():
        component.to_csv(output_dir / f"factor_component_{name}.csv")
    for name, rank in factor_ranks.items():
        rank.to_csv(output_dir / f"factor_rank_{name}.csv")
    weights.to_csv(output_dir / "signal_weights_raw.csv")
    for name, signal_series in timing_signals.items():
        signal_series.to_csv(output_dir / f"{name}.csv", header=["timing_signal"])
    simulation.target_weights.to_csv(output_dir / "target_weights_executed.csv")
    simulation.actual_weights.to_csv(output_dir / "actual_weights.csv")
    simulation.positions.to_csv(output_dir / "positions.csv")
    equity_curve.to_csv(output_dir / "equity_curve.csv", header=["equity"])
    returns.to_csv(output_dir / "returns.csv", header=["returns"])
    simulation.costs.to_csv(output_dir / "daily_costs.csv")
    if not simulation.trades.empty:
        simulation.trades.to_csv(output_dir / "trades.csv", index=False)
    selected_symbols = (
        simulation.actual_weights.gt(0)
        .apply(lambda row: ",".join(row.index[row].tolist()), axis=1)
        .rename("selected_symbols")
    )
    selected_symbols.to_csv(output_dir / "selected_symbols.csv", header=True)
    for name, data in stock_timing_outputs.items():
        data.to_csv(output_dir / f"{name}.csv")
    for name, series in regime_outputs.items():
        series.to_csv(output_dir / f"{name}.csv", header=[name])
    if universe_mask is not None:
        universe_mask.astype(int).to_csv(output_dir / "universe_mask.csv")
    contribution.to_csv(output_dir / "symbol_contribution_daily.csv")
    contribution_summary.to_csv(output_dir / "symbol_contribution_summary.csv")
    write_json(metrics, output_dir / "metrics.json")
    write_json(execution_config, output_dir / "execution_assumptions.json")

    if strategy_config["output"].get("plot", True):
        plot_equity_curve(
            equity_curve=equity_curve,
            benchmark_equity=benchmark_equity,
            output_path=output_dir / "equity_curve.png",
            title=strategy_config["name"],
        )

    return {
        "output_dir": str(output_dir),
        "metrics": metrics,
        "symbols": symbols,
    }
