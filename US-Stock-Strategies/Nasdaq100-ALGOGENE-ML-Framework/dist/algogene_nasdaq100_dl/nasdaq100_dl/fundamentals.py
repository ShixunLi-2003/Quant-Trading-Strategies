"""Strict point-in-time access to a raw company-financials master table.

This module deliberately does not calculate PE, growth, margins, or any other
factor. It validates publication timestamps and exposes backward as-of views,
so model code cannot accidentally join a future filing to a past sample.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


RESERVED_COLUMNS = {
    "symbol", "filed_at", "effective_at", "report_date", "filing_id",
    "form_type", "source_url", "currency", "fiscal_period",
}


def _timestamps(values):
    return pd.to_datetime(values, utc=True, errors="coerce")


def load_point_in_time_fundamentals(path, availability_lag_hours=24):
    """Load a raw financial table and derive its earliest safe use timestamp.

    ``filed_at`` must be the public filing/release timestamp, not the fiscal
    period end. A non-negative safety lag is always applied. Date-only values
    therefore become usable no earlier than the following day by default.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    aliases = {
        "ticker": "symbol",
        "filing_date": "filed_at",
        "filingDate": "filed_at",
        "published_at": "filed_at",
        "publication_time": "filed_at",
        "reportDate": "report_date",
    }
    frame = frame.rename(columns={name: target for name, target in aliases.items()
                                  if name in frame.columns and target not in frame.columns})
    missing = [name for name in ("symbol", "filed_at") if name not in frame.columns]
    if missing:
        raise ValueError(
            "financial table requires public disclosure fields, missing: " +
            ", ".join(missing) + "; report_date cannot replace filed_at")
    lag = float(availability_lag_hours)
    if lag < 0:
        raise ValueError("availability_lag_hours cannot be negative")
    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["filed_at"] = _timestamps(frame["filed_at"])
    if "report_date" in frame:
        frame["report_date"] = _timestamps(frame["report_date"])
    frame["effective_at"] = frame["filed_at"] + pd.to_timedelta(lag, unit="h")
    invalid = frame["symbol"].eq("") | frame["filed_at"].isna()
    if invalid.any():
        raise ValueError("financial table contains blank symbols or invalid filed_at values")
    identity = ["symbol", "filed_at"]
    if "filing_id" in frame:
        identity.append("filing_id")
    if frame.duplicated(identity).any():
        raise ValueError("financial table contains duplicate filing identities")
    return frame.sort_values(["symbol", "effective_at"]).reset_index(drop=True)


def selectable_numeric_columns(financials):
    """Return raw numeric fields teammates may explicitly choose as inputs."""
    columns = []
    for column in financials.columns:
        if column in RESERVED_COLUMNS:
            continue
        values = pd.to_numeric(financials[column], errors="coerce")
        if values.notna().any():
            columns.append(column)
    return columns


def resolve_feature_columns(financials, config=None):
    """Validate the explicit raw fields selected by the model owner."""
    config = dict(config or {})
    requested = list(config.get("feature_columns", []))
    if requested == ["*"]:
        requested = selectable_numeric_columns(financials)
    if len(requested) != len(set(requested)):
        raise ValueError("financial feature_columns contains duplicates")
    forbidden = [name for name in requested if name in RESERVED_COLUMNS]
    if forbidden:
        raise ValueError("metadata cannot be model features: " + ", ".join(forbidden))
    missing = [name for name in requested if name not in financials.columns]
    if missing:
        raise ValueError("financial feature columns not found: " + ", ".join(missing))
    nonnumeric = []
    for name in requested:
        if pd.to_numeric(financials[name], errors="coerce").notna().sum() == 0:
            nonnumeric.append(name)
    if nonnumeric:
        raise ValueError("financial feature columns contain no numeric values: " +
                         ", ".join(nonnumeric))
    return requested


def output_feature_columns(source_columns, prefix="fin_"):
    return [prefix + name for name in source_columns]


def safe_financial_snapshot(financials, as_of):
    """Return only the latest filing per symbol that was public by ``as_of``."""
    moment = pd.Timestamp(as_of)
    if moment.tzinfo is None:
        moment = moment.tz_localize("UTC")
    else:
        moment = moment.tz_convert("UTC")
    visible = financials[financials["effective_at"].le(moment)]
    if visible.empty:
        return visible.copy()
    return visible.sort_values("effective_at").groupby("symbol", as_index=False).tail(1)


def attach_point_in_time_fundamentals(panel, financials, config=None):
    """Backward as-of join selected raw columns and retain audit timestamps."""
    config = dict(config or {})
    source_columns = resolve_feature_columns(financials, config)
    prefix = str(config.get("feature_prefix", "fin_"))
    selected_outputs = output_feature_columns(source_columns, prefix)
    if panel.empty:
        result = panel.copy()
        result["financial_effective_at"] = pd.Series(dtype="datetime64[ns, UTC]")
        for column in selected_outputs:
            result[column] = pd.Series(dtype=float)
        return result
    if not source_columns:
        return panel.copy()

    right_columns = ["symbol", "effective_at"] + source_columns
    raw = financials[right_columns].copy()
    for column in source_columns:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    pieces = []
    for symbol, left in panel.groupby("symbol", sort=False):
        right = raw[raw["symbol"].eq(symbol)].drop(columns=["symbol"]).sort_values("effective_at")
        ordered = left.copy()
        ordered["_prediction_at"] = pd.to_datetime(
            ordered["trade_date"], utc=True, errors="coerce") + pd.Timedelta(hours=23, minutes=59)
        ordered = ordered.sort_values("_prediction_at")
        if right.empty:
            joined = ordered.copy()
            joined["effective_at"] = pd.NaT
            for column in source_columns:
                joined[column] = np.nan
        else:
            joined = pd.merge_asof(
                ordered, right, left_on="_prediction_at", right_on="effective_at",
                direction="backward", allow_exact_matches=True)
        pieces.append(joined)
    result = pd.concat(pieces, ignore_index=True)
    result = result.rename(columns={"effective_at": "financial_effective_at"})
    result = result.rename(columns={name: prefix + name for name in source_columns})
    audit_no_future_financials(result)
    return result.drop(columns=["_prediction_at"]).sort_values(
        ["trade_date", "symbol"]).reset_index(drop=True)


def audit_no_future_financials(frame):
    """Hard failure if a merged feature was unavailable at prediction time."""
    if "financial_effective_at" not in frame:
        return True
    prediction = pd.to_datetime(frame["trade_date"], utc=True, errors="coerce") + pd.Timedelta(
        hours=23, minutes=59)
    source = pd.to_datetime(frame["financial_effective_at"], utc=True, errors="coerce")
    violation = source.notna() & source.gt(prediction)
    if violation.any():
        examples = frame.loc[violation, ["symbol", "trade_date", "financial_effective_at"]]
        raise RuntimeError("future financial data detected: " +
                           examples.head(5).to_json(orient="records", date_format="iso"))
    return True


def fundamental_coverage(frame, feature_columns):
    if frame.empty or not feature_columns:
        return 0.0
    return float(frame[feature_columns].notna().all(axis=1).mean())
