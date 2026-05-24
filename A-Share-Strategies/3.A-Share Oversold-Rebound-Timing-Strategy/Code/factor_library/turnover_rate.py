"""Turnover-rate factor used by the strategy."""

import pandas as pd
fin_cols = []

def add_factor(df: pd.DataFrame, param=None, **kwargs) -> (pd.DataFrame, dict):
    col_name = kwargs['col_name']
    turnover_rate = df['turnover'] / df['float_market_cap']
    df[col_name] = turnover_rate.rolling(param).mean()
    agg_rules = {col_name: 'last'}
    return (df[[col_name]], agg_rules)
