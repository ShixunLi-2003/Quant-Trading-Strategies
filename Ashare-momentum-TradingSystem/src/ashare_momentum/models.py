from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.base import RegressorMixin


def winsorize_cross_section(
    series: pd.Series,
    dates: pd.Series,
    lower: float = 0.05,
    upper: float = 0.95,
) -> pd.Series:
    frame = pd.DataFrame({"value": series, "date": dates})
    lower_bound = frame.groupby("date")["value"].transform(lambda values: values.quantile(lower))
    upper_bound = frame.groupby("date")["value"].transform(lambda values: values.quantile(upper))
    return frame["value"].clip(lower_bound, upper_bound)


def walk_forward_predictions(
    panel: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    model_factory: Callable[[], RegressorMixin],
    train_days: int = 120,
    embargo_days: int = 3,
    minimum_train_rows: int = 500,
) -> pd.DataFrame:
    working = panel.copy()
    working["trade_date"] = pd.to_datetime(working["trade_date"]).dt.normalize()
    dates = sorted(working["trade_date"].dropna().unique())
    predictions: list[pd.DataFrame] = []
    for index, test_date in enumerate(dates):
        training_end = index - embargo_days
        if training_end <= train_days:
            continue
        training_dates = dates[max(0, training_end - train_days) : training_end]
        train = working[working["trade_date"].isin(training_dates)].dropna(
            subset=feature_columns + [target_column]
        )
        test = working[working["trade_date"] == test_date].dropna(subset=feature_columns)
        if len(train) < minimum_train_rows or test.empty:
            continue
        target = train[target_column] - train.groupby("trade_date")[target_column].transform("median")
        target = winsorize_cross_section(target, train["trade_date"])
        model = model_factory()
        model.fit(train[feature_columns], target)
        predictions.append(
            pd.DataFrame(
                {
                    "trade_date": test["trade_date"],
                    "stock_code": test["stock_code"],
                    "model_score": np.asarray(model.predict(test[feature_columns]), dtype=float),
                }
            )
        )
    if not predictions:
        return pd.DataFrame(columns=["trade_date", "stock_code", "model_score"])
    return pd.concat(predictions, ignore_index=True)


def rolling_splits(
    dates: list[pd.Timestamp],
    train_size: int,
    test_size: int,
    step: int,
) -> list[tuple[list[pd.Timestamp], list[pd.Timestamp]]]:
    splits: list[tuple[list[pd.Timestamp], list[pd.Timestamp]]] = []
    start = 0
    while start + train_size + test_size <= len(dates):
        train = dates[start : start + train_size]
        test = dates[start + train_size : start + train_size + test_size]
        splits.append((train, test))
        start += step
    return splits
