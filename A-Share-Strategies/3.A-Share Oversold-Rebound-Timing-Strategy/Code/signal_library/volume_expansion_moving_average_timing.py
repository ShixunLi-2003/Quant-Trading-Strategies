"""Combine volume-expansion timing and equity moving-average timing."""

import pandas as pd

from signal_library.moving_average_timing import equity_signal as equity_ma_timing_signal
from signal_library.volume_expansion_timing import equity_signal as volume_timing_signal


def equity_signal(equity_df: pd.DataFrame, *args) -> pd.Series:
    """Go long only when both component signals are long."""
    equity_df = equity_df.copy().reset_index(drop=True)
    volume_n = int(args[0])
    volume_threshold = float(args[1])
    equity_ma_n = int(args[2])
    signal1 = volume_timing_signal(equity_df, volume_n, volume_threshold)
    signal2 = equity_ma_timing_signal(equity_df, equity_ma_n)
    return ((signal1 == 1) & (signal2 == 1)).astype(float)
