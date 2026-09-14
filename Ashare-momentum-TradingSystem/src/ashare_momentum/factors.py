from __future__ import annotations

import numpy as np
import pandas as pd


FACTOR_COLUMNS = [
    "d_ret_1",
    "d_ret_3",
    "d_ret_5",
    "d_amp_1",
    "d_amount_ratio_5",
    "d_close_to_ma5",
    "d_close_to_ma20",
    "m_intraday_ret",
    "m_first_30_ret",
    "m_first_60_ret",
    "m_last_30_ret",
    "m_close_position",
    "m_realized_vol",
    "m_up_minute_ratio",
    "m_amount_last30_ratio",
    "m_vwap_gap",
]

LOW_VOLATILITY_SIGNS = {
    "m_last_30_ret": -1.0,
    "m_realized_vol": -1.0,
    "d_amp_1": -1.0,
    "m_vwap_gap": -1.0,
    "m_first_60_ret": 1.0,
    "m_first_30_ret": 1.0,
}


def build_daily_factors(daily: pd.DataFrame, horizon: int) -> pd.DataFrame:
    groups: list[pd.DataFrame] = []
    for _, stock in daily.groupby("stock_code", sort=False):
        output = stock.sort_values("trade_date").copy()
        close = output["close"].astype(float)
        amount = output["amount"].astype(float)
        output["d_ret_1"] = close.pct_change(1)
        output["d_ret_3"] = close.pct_change(3)
        output["d_ret_5"] = close.pct_change(5)
        output["d_amp_1"] = (output["high"] - output["low"]) / close.replace(0, np.nan)
        output["d_amount_ratio_5"] = amount / amount.rolling(5, min_periods=3).mean()
        output["d_close_to_ma5"] = close / close.rolling(5, min_periods=3).mean() - 1.0
        output["d_close_to_ma20"] = close / close.rolling(20, min_periods=10).mean() - 1.0
        output[f"fwd_ret_{horizon}d"] = close.shift(-horizon) / close - 1.0
        groups.append(output)
    return pd.concat(groups, ignore_index=True)


def build_minute_factors(minute: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (stock_code, trade_date), bars in minute.groupby(["stock_code", "trade_date"], sort=True):
        bars = bars.sort_values("datetime")
        if len(bars) < 120:
            continue
        first_30 = bars.iloc[:30]
        first_60 = bars.iloc[:60]
        last_30 = bars.iloc[-30:]
        close = bars["close"].astype(float)
        minute_returns = close.pct_change().replace([np.inf, -np.inf], np.nan)
        total_amount = float(bars["amount"].sum())
        total_volume = float(bars["volume"].sum())
        vwap = total_amount / (total_volume * 100.0) if total_volume > 0 else np.nan
        session_open = float(bars["open"].iloc[0])
        session_close = float(close.iloc[-1])
        session_high = float(bars["high"].max())
        session_low = float(bars["low"].min())
        rows.append(
            {
                "stock_code": stock_code,
                "trade_date": trade_date,
                "m_intraday_ret": session_close / session_open - 1.0,
                "m_first_30_ret": float(first_30["close"].iloc[-1]) / float(first_30["open"].iloc[0]) - 1.0,
                "m_first_60_ret": float(first_60["close"].iloc[-1]) / float(first_60["open"].iloc[0]) - 1.0,
                "m_last_30_ret": float(last_30["close"].iloc[-1]) / float(last_30["open"].iloc[0]) - 1.0,
                "m_close_position": (session_close - session_low) / (session_high - session_low)
                if session_high > session_low
                else np.nan,
                "m_realized_vol": float(minute_returns.std()),
                "m_up_minute_ratio": float((minute_returns > 0).mean()),
                "m_amount_last30_ratio": float(last_30["amount"].sum() / (total_amount / 8.0))
                if total_amount > 0
                else np.nan,
                "m_vwap_gap": session_close / vwap - 1.0 if np.isfinite(vwap) and vwap > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def cross_sectional_zscore(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = frame.copy()
    for column in columns:
        grouped = output.groupby("trade_date")[column]
        output[f"z_{column}"] = (output[column] - grouped.transform("mean")) / grouped.transform(
            "std"
        ).replace(0, np.nan)
    return output


def build_factor_panel(daily: pd.DataFrame, minute: pd.DataFrame, horizon: int = 3) -> pd.DataFrame:
    daily_factors = build_daily_factors(daily, horizon)
    minute_factors = build_minute_factors(minute)
    panel = daily_factors.merge(minute_factors, on=["stock_code", "trade_date"], how="inner")
    return panel.dropna(subset=[f"fwd_ret_{horizon}d"]).reset_index(drop=True)


def low_volatility_score(panel: pd.DataFrame, weight: float = 0.6) -> pd.Series:
    standardized = cross_sectional_zscore(panel, FACTOR_COLUMNS)
    momentum = standardized[[f"z_{column}" for column in FACTOR_COLUMNS]].mean(axis=1)
    defensive = pd.concat(
        [standardized[f"z_{column}"] * sign for column, sign in LOW_VOLATILITY_SIGNS.items()],
        axis=1,
    ).mean(axis=1)
    return (1.0 - weight) * momentum + weight * defensive
