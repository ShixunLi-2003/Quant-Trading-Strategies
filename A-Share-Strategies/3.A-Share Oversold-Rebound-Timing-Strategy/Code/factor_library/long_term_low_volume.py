"""Long-term low-volume factor used by the strategy."""

import pandas as pd
fin_cols = []

def add_factor(df: pd.DataFrame, param=None, **kwargs) -> (pd.DataFrame, dict):
    col_name = kwargs['col_name']
    n_days = int(param)
    df[col_name] = df['volume'].rolling(window=n_days, min_periods=1).mean()
    agg_rules = {col_name: 'last'}
    return (df[[col_name]], agg_rules)
