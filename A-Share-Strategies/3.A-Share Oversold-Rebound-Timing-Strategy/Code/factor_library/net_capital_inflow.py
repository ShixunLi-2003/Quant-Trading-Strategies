"""Net-capital-inflow factor used by the strategy."""

import pandas as pd
fin_cols = []

def add_factor(df: pd.DataFrame, param, fin_data=None, **kwargs) -> (pd.DataFrame, dict):
    col_name = kwargs['col_name']
    n = param[0]
    daily_flow = df['return'] * df['turnover']
    factor_col = daily_flow.rolling(n).sum()
    factor_df = pd.DataFrame({col_name: factor_col}, index=df.index)
    agg_dict = {col_name: 'last'}
    return (factor_df, agg_dict)
