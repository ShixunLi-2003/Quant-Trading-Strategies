"""
Market Data Adapters

Normalizes stock and index CSV inputs into a consistent OHLCV schema for downstream analysis and backtests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def normalize_stock_history(data: pd.DataFrame) -> pd.DataFrame:
    renamed = data.rename(
        columns={
            "timetag": "date",
            "volumn": "volume",
            "open_ineterst": "open_interest",
        }
    ).copy()
    renamed["date"] = pd.to_datetime(renamed["date"].astype(str), format="%Y%m%d")
    for column in ["open", "high", "low", "close", "volume", "amount", "open_interest"]:
        if column in renamed.columns:
            renamed[column] = pd.to_numeric(renamed[column], errors="coerce")
    for column in ["open", "high", "low", "close"]:
        if column in renamed.columns:
            renamed.loc[renamed[column] <= 0, column] = pd.NA
    renamed = renamed.set_index("date").sort_index()
    return renamed


def load_and_normalize_stock_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    return normalize_stock_history(raw)


def load_and_normalize_index_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path, skiprows=[1, 2])
    raw = raw.rename(
        columns={
            "Price": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    raw["date"] = pd.to_datetime(raw["date"])
    for column in ["open", "high", "low", "close", "adj_close", "volume"]:
        if column in raw.columns:
            raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw = raw.set_index("date").sort_index()
    return raw
