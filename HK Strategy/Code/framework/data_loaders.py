"""
Data Loading Utilities

Resolves universes, loads panel data for the HK equity universe, and loads benchmark series.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from hk_quant.config import resolve_path
from hk_quant.data.adapters import load_and_normalize_index_csv, load_and_normalize_stock_csv


def normalize_symbol(symbol: str | int) -> str:
    return str(symbol).strip().zfill(5)


def _project_base_dir(project_config: dict) -> Path:
    return Path(project_config["_meta"]["base_dir"]).resolve()


def _stock_data_dir(project_config: dict) -> Path:
    return resolve_path(_project_base_dir(project_config), project_config["stock_data_dir"])


def _index_data_dir(project_config: dict) -> Path:
    return resolve_path(_project_base_dir(project_config), project_config["index_data_dir"])


def _apply_date_range(frame: pd.DataFrame | pd.Series, start: str | None, end: str | None):
    if start:
        frame = frame.loc[pd.Timestamp(start) :]
    if end:
        frame = frame.loc[: pd.Timestamp(end)]
    return frame


def list_available_symbols(project_config: dict) -> list[str]:
    stock_dir = _stock_data_dir(project_config)
    pattern = re.compile(r"price_(\d{5})\.csv$", re.IGNORECASE)
    symbols = []
    for path in stock_dir.glob("price_*.csv"):
        match = pattern.search(path.name)
        if match:
            symbols.append(match.group(1))
    return sorted(symbols)


def resolve_universe_symbols(universe_config: dict, project_config: dict) -> list[str]:
    mode = universe_config.get("mode", "manual")
    if mode == "manual":
        symbols = [normalize_symbol(symbol) for symbol in universe_config.get("symbols", [])]
    elif mode == "scan_all":
        symbols = list_available_symbols(project_config)
    else:
        raise ValueError(f"Unsupported universe mode: {mode}")
    limit = universe_config.get("limit")
    if limit:
        symbols = symbols[: int(limit)]
    if not symbols:
        raise ValueError("Universe is empty after resolution.")
    return symbols


def load_stock_history(
    symbol: str | int,
    project_config: dict,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    stock_dir = _stock_data_dir(project_config)
    symbol = normalize_symbol(symbol)
    path = stock_dir / f"price_{symbol}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Stock CSV not found: {path}")
    data = load_and_normalize_stock_csv(path)
    return _apply_date_range(data, start, end)


def load_price_matrix(
    symbols: Iterable[str],
    field: str,
    project_config: dict,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    series_list = []
    for symbol in symbols:
        history = load_stock_history(symbol, project_config, start=start, end=end)
        if field not in history.columns:
            raise KeyError(f"Field '{field}' not found in stock history for {symbol}.")
        series = history[field].rename(normalize_symbol(symbol))
        series_list.append(series)
    matrix = pd.concat(series_list, axis=1).sort_index()
    return matrix


def load_market_data(
    symbols: Iterable[str],
    fields: Iterable[str],
    project_config: dict,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, pd.DataFrame]:
    field_list = list(fields)
    return {
        field: load_price_matrix(symbols, field=field, project_config=project_config, start=start, end=end)
        for field in field_list
    }


def load_benchmark_series(project_config: dict, benchmark_config: dict | None, start: str | None, end: str | None) -> pd.Series | None:
    if not benchmark_config:
        return None
    if benchmark_config.get("use_default"):
        benchmark_config = project_config.get("default_benchmark")
    if not benchmark_config:
        return None

    benchmark_type = benchmark_config.get("type", "index_csv")
    price_field = benchmark_config.get("price_field", "close")
    if benchmark_type == "index_csv":
        path = resolve_path(_project_base_dir(project_config), benchmark_config["path"])
        data = load_and_normalize_index_csv(path)
        series = data[price_field].rename(Path(path).stem)
    elif benchmark_type == "index_composite_csv":
        paths = benchmark_config.get("paths", [])
        if not paths:
            raise ValueError("index_composite_csv benchmark requires non-empty 'paths'.")
        series_list = []
        for raw_path in paths:
            path = resolve_path(_project_base_dir(project_config), raw_path)
            data = load_and_normalize_index_csv(path)
            price = data[price_field].rename(Path(path).stem)
            series_list.append(price)
        frame = pd.concat(series_list, axis=1).sort_index().ffill()
        returns = frame.pct_change(fill_method=None).fillna(0.0)
        composite_returns = returns.mean(axis=1)
        composite_price = (1.0 + composite_returns).cumprod()
        composite_price.iloc[0] = 1.0
        series = composite_price.rename("index_composite")
    elif benchmark_type == "stock_symbol":
        symbol = benchmark_config["symbol"]
        data = load_stock_history(symbol, project_config, start=start, end=end)
        series = data[price_field].rename(normalize_symbol(symbol))
    else:
        raise ValueError(f"Unsupported benchmark type: {benchmark_type}")
    return _apply_date_range(series, start, end)
