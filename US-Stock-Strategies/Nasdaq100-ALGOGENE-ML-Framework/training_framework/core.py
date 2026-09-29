from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from contracts import checked_predict, load_model
from fundamentals import (attach_point_in_time_fundamentals,
                          fundamental_coverage, output_feature_columns,
                          resolve_feature_columns)


BASE_FEATURES = [
    "ret_1d", "ret_3d", "ret_5d", "close_to_ma5", "close_to_ma20",
    "intraday_ret", "first_30_ret", "first_60_ret", "last_30_ret",
    "realized_vol", "up_minute_ratio", "close_position",
]


def select_dataset_columns(available_columns, requested_columns, financial_prefix="fin_"):
    """Expand the two supported wildcards and validate the model feature set."""
    requested = list(requested_columns or ["*"])
    selected = []
    for name in requested:
        if name == "*":
            selected.extend(column for column in available_columns
                            if not column.startswith(financial_prefix))
        elif name == financial_prefix + "*":
            selected.extend(column for column in available_columns
                            if column.startswith(financial_prefix))
        else:
            selected.append(name)
    selected = list(dict.fromkeys(selected))
    missing = [name for name in selected if name not in available_columns]
    if missing:
        raise ValueError(
            "dataset_columns unavailable: {}. Available columns: {}".format(
                ", ".join(missing), ", ".join(available_columns)))
    if not selected:
        raise ValueError("dataset_columns selected no model features")
    return selected


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(temporary), str(path))


def environment_probe(getter=None):
    modules = {}
    for name in ("numpy", "pandas", "sklearn", "tensorflow", "torch", "joblib"):
        try:
            module = __import__(name)
            modules[name] = getattr(module, "__version__", "available")
        except Exception as exc:
            modules[name] = "unavailable: " + type(exc).__name__
    result = {
        "python": sys.version,
        "platform": platform.platform(),
        "modules": modules,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
    }
    if getter is not None:
        try:
            sample = getter({"instrument": "AAPL"}, 5, "D", datetime.utcnow().strftime("%Y-%m-%d"))
            result["algogene_history_rows"] = len(sample or {})
        except Exception as exc:
            result["algogene_history_error"] = type(exc).__name__ + ": " + str(exc)[:200]
    return result


def _parse_page(raw, symbol):
    values = list(raw.values()) if isinstance(raw, dict) else list(raw or [])
    rows = []
    for item in values:
        if not isinstance(item, dict) or not item.get("t"):
            continue
        rows.append({
            "symbol": symbol,
            "time": item.get("t"),
            "close": item.get("c"),
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["time"] = pd.to_datetime(frame["time"], utc=True, errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    return frame.dropna().query("close > 0").drop_duplicates("time").sort_values("time")


def fetch_history(getter, symbol, start, end, interval="M", page_size=5000,
                  max_pages=1000):
    start_ts = pd.Timestamp(start, tz="UTC")
    cursor = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    pages = []
    previous_oldest = None
    for _ in range(int(max_pages)):
        raw = getter({"instrument": symbol}, int(page_size), interval,
                     cursor.strftime("%Y-%m-%d %H:%M:%S"))
        page = _parse_page(raw, symbol)
        if page.empty:
            break
        pages.append(page)
        oldest = page["time"].min()
        if oldest <= start_ts or oldest == previous_oldest:
            break
        previous_oldest = oldest
        cursor = oldest - pd.Timedelta(seconds=1)
    if not pages:
        return pd.DataFrame(columns=["symbol", "time", "close"])
    frame = pd.concat(pages, ignore_index=True).drop_duplicates("time").sort_values("time")
    return frame[(frame["time"] >= start_ts) & (frame["time"] <= pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1))]


def _daily_close_features(prices):
    prices = np.asarray(prices, dtype=float)
    if len(prices) < 2 or np.any(~np.isfinite(prices)) or np.any(prices <= 0):
        return None
    returns = prices[1:] / prices[:-1] - 1.0
    first30 = prices[:min(30, len(prices))]
    first60 = prices[:min(60, len(prices))]
    last30 = prices[-min(30, len(prices)):]
    low, high = float(np.min(prices)), float(np.max(prices))
    return {
        "open": float(prices[0]),
        "close": float(prices[-1]),
        "intraday_ret": float(prices[-1] / prices[0] - 1.0),
        "first_30_ret": float(first30[-1] / first30[0] - 1.0),
        "first_60_ret": float(first60[-1] / first60[0] - 1.0),
        "last_30_ret": float(last30[-1] / last30[0] - 1.0),
        "realized_vol": float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0,
        "up_minute_ratio": float(np.mean(returns > 0)),
        "close_position": float((prices[-1] - low) / (high - low)) if high > low else 0.5,
        "minute_count": int(len(prices)),
    }


def minute_to_daily(frame, timezone="America/New_York", regular_session_only=True):
    if frame.empty:
        return pd.DataFrame()
    work = frame.copy()
    local = work["time"].dt.tz_convert(timezone)
    if regular_session_only:
        minutes = local.dt.hour * 60 + local.dt.minute
        work = work[(minutes > 570) & (minutes <= 960)].copy()
        local = work["time"].dt.tz_convert(timezone)
    work["trade_date"] = local.dt.tz_localize(None).dt.normalize()
    records = []
    for (symbol, trade_date), group in work.groupby(["symbol", "trade_date"], sort=True):
        values = _daily_close_features(group.sort_values("time")["close"].values)
        if values is not None:
            values.update({"symbol": symbol, "trade_date": trade_date})
            records.append(values)
    daily = pd.DataFrame(records)
    if daily.empty:
        return daily
    daily = daily.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    grouped = daily.groupby("symbol", sort=False)["close"]
    daily["ret_1d"] = grouped.pct_change(1)
    daily["ret_3d"] = grouped.pct_change(3)
    daily["ret_5d"] = grouped.pct_change(5)
    daily["close_to_ma5"] = daily["close"] / grouped.transform(lambda x: x.rolling(5).mean()) - 1.0
    daily["close_to_ma20"] = daily["close"] / grouped.transform(lambda x: x.rolling(20).mean()) - 1.0
    grouped_open = daily.groupby("symbol", sort=False)["open"]
    grouped_date = daily.groupby("symbol", sort=False)["trade_date"]
    daily["entry_date"] = grouped_date.shift(-1)
    daily["exit_date"] = grouped_date.shift(-2)
    daily["entry_price"] = grouped_open.shift(-1)
    daily["exit_price"] = grouped_open.shift(-2)
    daily["forward_return"] = daily["exit_price"] / daily["entry_price"] - 1.0
    return daily


def load_or_fetch_features(getter, symbol, config, cache_root, is_context=False):
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / (("context_" if is_context else "stock_") + symbol + ".csv.gz")
    if target.exists():
        cached = pd.read_csv(target, parse_dates=["trade_date"])
        if not cached.empty and cached["trade_date"].min() <= pd.Timestamp(config.start) and cached["trade_date"].max() >= pd.Timestamp(config.end) - pd.Timedelta(days=7):
            return cached
    bars = fetch_history(getter, symbol, config.start, config.end, config.interval,
                         config.page_size, config.max_pages_per_symbol)
    daily = minute_to_daily(bars, config.timezone, config.regular_session_only)
    if not daily.empty:
        daily.to_csv(target, index=False, compression="gzip")
    return daily


def build_panel(getter, symbols, config, cache_root, progress=print,
                fundamentals=None, fundamental_config=None):
    stock_frames = []
    for index, symbol in enumerate(symbols, 1):
        frame = load_or_fetch_features(getter, symbol, config, cache_root)
        if not frame.empty:
            stock_frames.append(frame)
        progress("STOCK {}/{} {} rows={}".format(index, len(symbols), symbol, len(frame)))
    if not stock_frames:
        raise RuntimeError("no stock data returned by ALGOGENE")
    panel = pd.concat(stock_frames, ignore_index=True)
    context_symbols = list(config.market_context) + list(config.sector_context)
    context_columns = []
    for index, symbol in enumerate(context_symbols, 1):
        context = load_or_fetch_features(getter, symbol, config, cache_root, True)
        safe = "".join(ch if ch.isalnum() else "_" for ch in symbol).lower()
        for source in ("ret_1d", "realized_vol"):
            column = "ctx_{}_{}".format(safe, source)
            context_columns.append(column)
            if context.empty or source not in context:
                panel[column] = 0.0
            else:
                mapped = context.drop_duplicates("trade_date").set_index("trade_date")[source]
                panel[column] = panel["trade_date"].map(mapped)
        progress("CONTEXT {}/{} {} rows={}".format(index, len(context_symbols), symbol, len(context)))
    panel["target_residual_return"] = panel["forward_return"] - panel.groupby("trade_date")["forward_return"].transform("median")
    available_columns = BASE_FEATURES + context_columns
    requested_columns = list(config.payload.get("dataset_columns", ["*"]))
    fundamental_config = dict(fundamental_config or {})
    financial_prefix = str(fundamental_config.get("feature_prefix", "fin_"))
    requested_financial = []
    for column in requested_columns:
        if column == financial_prefix + "*":
            requested_financial = ["*"]
            break
        if column.startswith(financial_prefix):
            requested_financial.append(column[len(financial_prefix):])
    fundamental_config["feature_columns"] = requested_financial
    if fundamental_config.get("enabled", False):
        source_columns = resolve_feature_columns(fundamentals, fundamental_config)
        financial_columns = output_feature_columns(
            source_columns, financial_prefix)
        panel = attach_point_in_time_fundamentals(
            panel, fundamentals, fundamental_config)
        available_columns += financial_columns
        coverage = fundamental_coverage(panel, financial_columns)
        progress("FINANCIAL_TABLE rows={} selected_features={} coverage={:.2%}".format(
            len(fundamentals), len(financial_columns), coverage))
        minimum_coverage = float(fundamental_config.get("minimum_coverage", 0.0))
        if financial_columns and coverage < minimum_coverage:
            raise RuntimeError(
                "financial feature coverage {:.2%} below required {:.2%}".format(
                    coverage, minimum_coverage))
    feature_columns = select_dataset_columns(
        available_columns, requested_columns, financial_prefix)
    panel[feature_columns] = panel[feature_columns].replace([np.inf, -np.inf], np.nan)
    panel[context_columns] = panel[context_columns].fillna(0.0)
    return panel, feature_columns


def _window_dates(dates, config):
    start = int(config.train_days) + int(config.validation_days) + int(config.embargo_days)
    for test_start in range(start, len(dates) - int(config.test_days) + 1, int(config.step_days)):
        validation_end = test_start - int(config.embargo_days)
        validation_start = validation_end - int(config.validation_days)
        train_start = validation_start - int(config.train_days)
        yield (dates[train_start:validation_start], dates[validation_start:validation_end],
               dates[test_start:test_start + int(config.test_days)])


def platform_like_backtest(frame, scores, config):
    """Approximate the platform's next-session, whole-share execution path."""
    columns = ["trade_date", "symbol", "forward_return"]
    for optional in ("entry_date", "exit_date", "entry_price", "exit_price"):
        if optional in frame:
            columns.append(optional)
    scored = frame[columns].copy()
    scored["score"] = np.asarray(scores, dtype=float)
    if "entry_price" not in scored:
        scored["entry_price"] = 1.0
        scored["exit_price"] = 1.0 + scored["forward_return"]
    if "entry_date" not in scored:
        scored["entry_date"] = scored["trade_date"]
        scored["exit_date"] = scored["trade_date"]
    top_n = int(config.payload.get("selection_top_n", 5))
    initial_capital = float(config.payload.get("initial_capital_usd", 10000))
    entry_slippage = float(config.payload.get("entry_slippage_bps", 2)) / 10000.0
    exit_slippage = float(config.payload.get("exit_slippage_bps", 2)) / 10000.0
    commission_rate = float(config.payload.get("commission_bps", 1)) / 10000.0
    minimum_commission = float(config.payload.get("minimum_commission_usd", 0))
    limit_buffer = float(config.payload.get("limit_buffer", 0.002))

    def commission(notional):
        return max(minimum_commission, abs(float(notional)) * commission_rate)

    capital = initial_capital
    nav = [capital]
    equity_rows, trade_rows = [], []
    for signal_date, group in scored.groupby("trade_date", sort=True):
        valid = group.replace([np.inf, -np.inf], np.nan).dropna(
            subset=["entry_price", "exit_price", "score"])
        valid = valid[(valid["entry_price"] > 0) & (valid["exit_price"] > 0)]
        selected = valid.nlargest(top_n, "score")
        starting_equity = capital
        cash = capital
        positions = []
        budget = starting_equity / max(top_n, 1)
        for _, row in selected.iterrows():
            buy_price = float(row["entry_price"]) * (
                1.0 + min(entry_slippage, limit_buffer))
            quantity = int(budget // buy_price)
            while quantity > 0:
                notional = quantity * buy_price
                buy_fee = commission(notional)
                if notional + buy_fee <= cash + 1e-9:
                    break
                quantity -= 1
            if quantity <= 0:
                continue
            notional = quantity * buy_price
            buy_fee = commission(notional)
            cash -= notional + buy_fee
            positions.append((row, quantity, buy_price, buy_fee))
        for row, quantity, buy_price, buy_fee in positions:
            sell_price = float(row["exit_price"]) * (1.0 - exit_slippage)
            sell_notional = quantity * sell_price
            sell_fee = commission(sell_notional)
            cash += sell_notional - sell_fee
            trade_rows.append({
                "signal_date": signal_date, "entry_date": row["entry_date"],
                "exit_date": row["exit_date"], "symbol": row["symbol"],
                "score": float(row["score"]), "quantity": int(quantity),
                "entry_price": buy_price, "exit_price": sell_price,
                "buy_commission": buy_fee, "sell_commission": sell_fee,
                "net_pnl": quantity * (sell_price - buy_price) - buy_fee - sell_fee,
            })
        capital = cash
        nav.append(capital)
        equity_rows.append({
            "signal_date": signal_date, "starting_equity_usd": starting_equity,
            "ending_equity_usd": capital,
            "net_return": capital / starting_equity - 1.0 if starting_equity else 0.0,
            "positions": len(positions),
        })
    if not equity_rows:
        metrics = {"total_net_return": -1.0, "max_drawdown": -1.0,
                   "ending_equity_usd": capital, "days": 0, "trades": 0}
        return metrics, pd.DataFrame(equity_rows), pd.DataFrame(trade_rows)
    values = np.asarray(nav, dtype=float)
    drawdown = values / np.maximum.accumulate(values) - 1.0
    metrics = {
        "total_net_return": float(capital / initial_capital - 1.0),
        "max_drawdown": float(drawdown.min()),
        "ending_equity_usd": float(capital),
        "days": len(equity_rows),
        "trades": len(trade_rows),
    }
    return metrics, pd.DataFrame(equity_rows), pd.DataFrame(trade_rows)


def validation_strategy_metrics(frame, scores, config):
    metrics, _, _ = platform_like_backtest(frame, scores, config)
    return metrics


def _objective_better(candidate, incumbent, tolerance):
    if incumbent is None:
        return True
    return_gap = candidate["total_net_return"] - incumbent["total_net_return"]
    if return_gap > tolerance:
        return True
    if abs(return_gap) <= tolerance:
        return candidate["max_drawdown"] > incumbent["max_drawdown"]
    return False


def train_walk_forward(panel, feature_columns, config, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    usable = panel.dropna(subset=feature_columns + ["target_residual_return"]).copy()
    dates = sorted(usable["trade_date"].unique())
    predictions, windows = [], []
    final_model = None
    for window_id, (train_dates, validation_dates, test_dates) in enumerate(_window_dates(dates, config), 1):
        train = usable[usable["trade_date"].isin(train_dates)]
        validation = usable[usable["trade_date"].isin(validation_dates)]
        test = usable[usable["trade_date"].isin(test_dates)]
        if len(train) < int(config.minimum_train_rows) or test.empty:
            continue
        candidates = config.payload.get("model_candidates") or [dict(config.model_params)]
        model, metrics, best_objective, best_index = None, None, None, None
        for candidate_index, parameters in enumerate(candidates):
            candidate_model = load_model(config.model_entrypoint, dict(parameters))
            candidate_metrics = candidate_model.fit(
                train[feature_columns].values, train["target_residual_return"].values,
                validation[feature_columns].values, validation["target_residual_return"].values)
            validation_scores = checked_predict(candidate_model, validation[feature_columns].values)
            objective = validation_strategy_metrics(validation, validation_scores, config)
            if _objective_better(objective, best_objective,
                                 float(config.payload.get("return_tie_tolerance", 0.0001))):
                model, metrics = candidate_model, dict(candidate_metrics or {})
                best_objective, best_index = objective, candidate_index
        metrics["selection_objective"] = best_objective
        metrics["selected_candidate_index"] = best_index
        scored_columns = ["trade_date", "symbol", "forward_return",
                          "target_residual_return"]
        scored_columns += [name for name in (
            "entry_date", "exit_date", "entry_price", "exit_price") if name in test]
        scored = test[scored_columns].copy()
        scored["model_score"] = checked_predict(model, test[feature_columns].values)
        scored["window_id"] = window_id
        predictions.append(scored)
        windows.append({
            "window_id": window_id,
            "train_start": str(pd.Timestamp(train_dates[0]).date()),
            "train_end": str(pd.Timestamp(train_dates[-1]).date()),
            "validation_start": str(pd.Timestamp(validation_dates[0]).date()),
            "validation_end": str(pd.Timestamp(validation_dates[-1]).date()),
            "test_start": str(pd.Timestamp(test_dates[0]).date()),
            "test_end": str(pd.Timestamp(test_dates[-1]).date()),
            "train_rows": int(len(train)), "test_rows": int(len(test)), "metrics": metrics,
        })
        final_model = model
    if final_model is None:
        raise RuntimeError("no rolling window met minimum_train_rows")
    model_path = output_dir / "model.joblib"
    final_model.save(model_path)
    result = pd.concat(predictions, ignore_index=True)
    result.to_csv(output_dir / "oos_predictions.csv.gz", index=False, compression="gzip")
    execution_metrics, equity_curve, trade_ledger = platform_like_backtest(
        result, result["model_score"].values, config)
    equity_curve.to_csv(output_dir / "jupyter_platform_like_equity.csv", index=False)
    trade_ledger.to_csv(output_dir / "jupyter_platform_like_trades.csv", index=False)
    atomic_json(output_dir / "jupyter_platform_like_metrics.json", execution_metrics)
    atomic_json(output_dir / "rolling_windows.json", windows)
    atomic_json(output_dir / "feature_schema.json", {"columns": feature_columns, "version": 2})
    sample = usable.tail(min(128, len(usable)))
    golden_prediction = checked_predict(final_model, sample[feature_columns].values)
    np.savez(output_dir / "golden_sample.npz", features=sample[feature_columns].values,
             prediction=golden_prediction)
    return result, windows, model_path


def sha256_path(path):
    digest = hashlib.sha256()
    path = Path(path)
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for item in files:
        digest.update(str(item.relative_to(path.parent)).replace("\\", "/").encode("utf-8"))
        with item.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def summarize_predictions(predictions, config=None):
    correlations = []
    for _, group in predictions.groupby("trade_date"):
        correlations.append(group["model_score"].corr(group["target_residual_return"]))
    daily_ic = pd.Series(correlations, dtype=float)
    summary = {"rows": int(len(predictions)),
               "windows": int(predictions["window_id"].nunique()),
               "mean_daily_ic": float(daily_ic.dropna().mean()) if daily_ic.notna().any() else None}
    if config is not None:
        execution, _, _ = platform_like_backtest(
            predictions, predictions["model_score"].values, config)
        summary["platform_like_execution"] = execution
    return summary
