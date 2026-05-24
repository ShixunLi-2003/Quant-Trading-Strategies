"""Generate a timing signal from the strategy equity curve and its moving average."""

import pandas as pd


def equity_signal(equity_df: pd.DataFrame, *args) -> pd.Series:
    """Stay invested only when the equity curve is above its trailing moving average."""
    lookback = int(args[0])
    moving_average = equity_df["nav"].rolling(lookback, min_periods=1).mean()
    return (equity_df["nav"] > moving_average).astype(float)
