from __future__ import annotations

from pathlib import Path

import pandas as pd


DAILY_COLUMNS = ["stock_code", "trade_date", "open", "high", "low", "close", "volume", "amount"]
MINUTE_COLUMNS = ["stock_code", "datetime", "open", "high", "low", "close", "volume", "amount"]


def read_market_table(path: str | Path, required_columns: list[str]) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported market-data format: {path.suffix}")
    missing = sorted(set(required_columns) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")
    return frame


def normalize_daily(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["trade_date"] = pd.to_datetime(output["trade_date"]).dt.normalize()
    output = output.sort_values(["stock_code", "trade_date"])
    return output.drop_duplicates(["stock_code", "trade_date"], keep="last").reset_index(drop=True)


def normalize_minute(frame: pd.DataFrame, timezone: str = "Asia/Shanghai") -> pd.DataFrame:
    output = frame.copy()
    timestamps = pd.to_datetime(output["datetime"], utc=True, errors="coerce")
    output["datetime"] = timestamps.dt.tz_convert(timezone)
    output["trade_date"] = output["datetime"].dt.tz_localize(None).dt.normalize()
    output["minute"] = output["datetime"].dt.hour * 100 + output["datetime"].dt.minute
    output = output.dropna(subset=["datetime"]).sort_values(["stock_code", "datetime"])
    return output.drop_duplicates(["stock_code", "datetime"], keep="last").reset_index(drop=True)


def enforce_point_in_time_universe(
    frame: pd.DataFrame,
    membership: pd.DataFrame,
    date_column: str = "trade_date",
) -> pd.DataFrame:
    members = membership[["stock_code", "effective_from", "effective_to"]].copy()
    members["effective_from"] = pd.to_datetime(members["effective_from"]).dt.normalize()
    members["effective_to"] = pd.to_datetime(members["effective_to"]).dt.normalize()
    candidates = frame.merge(members, on="stock_code", how="inner")
    dates = pd.to_datetime(candidates[date_column]).dt.normalize()
    mask = dates.ge(candidates["effective_from"]) & dates.le(candidates["effective_to"])
    return candidates.loc[mask].drop(columns=["effective_from", "effective_to"]).reset_index(drop=True)

