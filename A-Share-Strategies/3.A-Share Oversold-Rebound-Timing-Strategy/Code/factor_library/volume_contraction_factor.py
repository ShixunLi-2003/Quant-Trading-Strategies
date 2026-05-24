"""Volume-contraction factor used by the strategy."""

import pandas as pd
fin_cols = []

def add_factor(df: pd.DataFrame, param, fin_data=None, **kwargs) -> (pd.DataFrame, dict):
    short = param[0]
    long = param[1]
    col_name = kwargs['col_name']
    short_mean = df['turnover'].rolling(short).mean()
    long_mean = df['turnover'].rolling(long).mean()
    factor_col = short_mean / long_mean
    factor_df = pd.DataFrame({col_name: factor_col}, index=df.index)
    agg_dict = {col_name: 'last'}
    return (factor_df, agg_dict)
