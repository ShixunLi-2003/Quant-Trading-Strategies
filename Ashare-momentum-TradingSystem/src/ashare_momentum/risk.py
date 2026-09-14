from __future__ import annotations

import pandas as pd


def build_etf_regime_table(
    etf_prices: pd.DataFrame,
    moving_average_days: int = 5,
) -> pd.DataFrame:
    prices = etf_prices.copy()
    prices["trade_date"] = pd.to_datetime(prices["trade_date"]).dt.normalize()
    prices = prices.sort_values(["stock_code", "trade_date"])
    grouped = prices.groupby("stock_code")["close"]
    prices["ma"] = grouped.transform(lambda values: values.rolling(moving_average_days).mean())
    prices["daily_return"] = grouped.pct_change()
    prices["positive_trend"] = prices["close"] > prices["ma"]
    return (
        prices.groupby("trade_date")
        .agg(
            breadth=("positive_trend", "mean"),
            median_return=("daily_return", "median"),
            etf_count=("stock_code", "nunique"),
        )
        .reset_index()
    )


def build_etf_exposure_schedule(
    regime: pd.DataFrame,
    breadth_threshold: float = 0.5,
    confirmation_days: int = 2,
    half_after: int = 2,
    cash_after: int = 3,
) -> pd.DataFrame:
    output = regime.sort_values("trade_date").copy()
    output["weak"] = output["breadth"] < breadth_threshold
    streak: list[int] = []
    count = 0
    for weak in output["weak"]:
        count = count + 1 if bool(weak) else 0
        streak.append(count)
    output["weak_streak"] = streak
    output["risk_exposure"] = 1.0
    output.loc[output["weak_streak"] >= max(confirmation_days, half_after), "risk_exposure"] = 0.5
    output.loc[output["weak_streak"] >= max(confirmation_days, cash_after), "risk_exposure"] = 0.0
    output["effective_trade_date"] = output["trade_date"].shift(-1)
    return output

