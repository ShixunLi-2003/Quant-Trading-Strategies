from __future__ import annotations

from pathlib import Path

import math
import pandas as pd

from hk_quant.analysis.performance import calculate_performance_metrics
from hk_quant.backtests.hk_execution import build_execution_config, calculate_hk_fees, get_board_lot, round_down_to_lot
from hk_quant.config import ensure_directory, write_json
from hk_quant.data.loaders import load_benchmark_series, load_stock_history
from hk_quant.visualization.plots import plot_equity_curve


def _require_backtrader():
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError("backtrader is not installed. Run `python -m pip install -r configs/requirements.txt` first.") from exc
    return bt


def _flatten_dict(data: dict, prefix: str = "") -> dict[str, object]:
    flat = {}
    for key, value in data.items():
        new_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(_flatten_dict(value, new_key))
        else:
            flat[new_key] = value
    return flat


def resolve_output_dir(project_config: dict, subdir: str) -> Path:
    root = Path(project_config["_meta"]["base_dir"]).resolve()
    output_root = (root / project_config["output_root"]).resolve()
    return output_root / subdir


def run_backtrader_strategy(project_config: dict, strategy_config: dict) -> dict[str, object]:
    bt = _require_backtrader()
    execution_config = build_execution_config(strategy_config)

    class PandasOHLCV(bt.feeds.PandasData):
        lines = ("amount",)
        params = (
            ("datetime", None),
            ("open", "open"),
            ("high", "high"),
            ("low", "low"),
            ("close", "close"),
            ("volume", "volume"),
            ("openinterest", -1),
            ("amount", "amount"),
        )

    class HongKongEquityCommissionInfo(bt.CommInfoBase):
        params = dict(stocklike=True, commtype=bt.CommInfoBase.COMM_FIXED)

        def _getcommission(self, size, price, pseudoexec):
            if size == 0 or price <= 0:
                return 0.0
            notional = abs(size) * price
            side = "buy" if size > 0 else "sell"
            return calculate_hk_fees(notional, side=side, execution_config=execution_config)["total"]

    class MovingAverageCrossStrategy(bt.Strategy):
        params = dict(
            fast=20,
            slow=60,
            size_pct=0.95,
            enable_benchmark_filter=False,
            benchmark_window=120,
            adv_window=20,
        )

        def __init__(self):
            self.fast_ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.fast)
            self.slow_ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.slow)
            self.cross = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
            self.avg_volume = bt.indicators.SimpleMovingAverage(self.data.volume, period=self.p.adv_window)
            self.avg_amount = bt.indicators.SimpleMovingAverage(self.data.amount, period=self.p.adv_window)
            self.benchmark_ma = None
            if len(self.datas) > 1 and self.p.enable_benchmark_filter:
                self.benchmark_ma = bt.indicators.SimpleMovingAverage(
                    self.datas[1].close, period=self.p.benchmark_window
                )
            self.pending_order = None

        def _is_tradable(self) -> bool:
            return (
                math.isfinite(self.data.close[0])
                and self.data.close[0] > 0
                and self.data.volume[0] > execution_config["min_daily_volume_shares"]
                and self.data.amount[0] > execution_config["min_daily_amount_hkd"]
            )

        def _max_fillable_shares(self) -> int:
            if not self._is_tradable():
                return 0
            lot_size = get_board_lot(symbol, execution_config)
            cap_by_volume = round_down_to_lot(
                self.avg_volume[0] * execution_config["max_participation_volume_ratio"],
                lot_size,
            )
            cap_by_amount = round_down_to_lot(
                self.avg_amount[0] * execution_config["max_participation_amount_ratio"] / max(self.data.close[0], 1e-9),
                lot_size,
            )
            return int(max(0, min(cap_by_volume, cap_by_amount)))

        def notify_order(self, order):
            if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
                self.pending_order = None

        def next(self):
            if self.pending_order is not None:
                return
            benchmark_ok = True
            if self.benchmark_ma is not None:
                benchmark_ok = self.datas[1].close[0] > self.benchmark_ma[0]

            lot_size = get_board_lot(symbol, execution_config)
            max_fillable = self._max_fillable_shares()

            if not self.position and self.cross[0] > 0 and benchmark_ok:
                target_value = self.broker.getvalue() * self.p.size_pct
                raw_size = target_value / max(self.data.close[0], 1e-9)
                size = round_down_to_lot(raw_size, lot_size)
                size = min(size, max_fillable)
                if size > 0:
                    self.pending_order = self.buy(size=size)
            elif self.position and (self.cross[0] < 0 or not benchmark_ok):
                size = round_down_to_lot(self.position.size, lot_size)
                size = min(size, max_fillable if max_fillable > 0 else size)
                if size > 0:
                    self.pending_order = self.sell(size=size)

    strategy_registry = {"ma_cross": MovingAverageCrossStrategy}

    start = strategy_config["date_range"]["start"]
    end = strategy_config["date_range"]["end"]
    symbol = strategy_config["symbol"]
    stock_data = load_stock_history(symbol, project_config, start=start, end=end).dropna(subset=["open", "high", "low", "close"])
    benchmark_series = load_benchmark_series(project_config, strategy_config.get("benchmark"), start=start, end=end)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(strategy_config["backtest"].get("initial_cash", 1_000_000))
    cerebro.broker.addcommissioninfo(HongKongEquityCommissionInfo())

    stock_feed = PandasOHLCV(dataname=stock_data)
    cerebro.adddata(stock_feed, name=str(symbol))

    benchmark_feed = None
    if benchmark_series is not None:
        benchmark_frame = pd.DataFrame(
            {
                "open": benchmark_series,
                "high": benchmark_series,
                "low": benchmark_series,
                "close": benchmark_series,
                "volume": 0.0,
            }
        )
        benchmark_feed = bt.feeds.PandasData(dataname=benchmark_frame)
        cerebro.adddata(benchmark_feed, name="benchmark")

    strategy_name = strategy_config["strategy"]["name"]
    strategy_cls = strategy_registry[strategy_name]
    cerebro.addstrategy(strategy_cls, **strategy_config["strategy"].get("params", {}))
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="timereturn")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    result = cerebro.run()[0]
    return_dict = result.analyzers.timereturn.get_analysis()
    returns = pd.Series(return_dict).sort_index()
    initial_cash = strategy_config["backtest"].get("initial_cash", 1_000_000)
    equity_curve = (1.0 + returns).cumprod() * initial_cash
    metrics = calculate_performance_metrics(returns, equity_curve=equity_curve)

    sharpe = result.analyzers.sharpe.get_analysis()
    drawdown = result.analyzers.drawdown.get_analysis()
    trades = result.analyzers.trades.get_analysis()
    metrics.update(
        {
            "backtrader_sharpe": sharpe.get("sharperatio"),
            "max_drawdown_pct": drawdown.get("max", {}).get("drawdown"),
        }
    )

    benchmark_equity = None
    if benchmark_series is not None:
        benchmark_returns = benchmark_series.pct_change().fillna(0.0)
        benchmark_equity = (1.0 + benchmark_returns).cumprod() * initial_cash
        metrics["benchmark_total_return"] = float(benchmark_equity.iloc[-1] / benchmark_equity.iloc[0] - 1.0)

    output_dir = ensure_directory(resolve_output_dir(project_config, strategy_config["output"]["subdir"]))
    stock_data.to_csv(output_dir / "input_data.csv")
    equity_curve.to_csv(output_dir / "equity_curve.csv", header=["equity"])
    returns.to_csv(output_dir / "returns.csv", header=["returns"])
    write_json(metrics, output_dir / "metrics.json")
    write_json(_flatten_dict(trades), output_dir / "trade_analysis.json")
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
        "symbol": symbol,
    }
