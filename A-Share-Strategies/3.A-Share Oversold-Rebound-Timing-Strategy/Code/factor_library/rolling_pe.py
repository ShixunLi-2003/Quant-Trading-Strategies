"""Rolling-PE filter factor used by the strategy."""

import pandas as pd
fin_cols = ['R_np@xbx']

def add_factor(df: pd.DataFrame, param=None, **kwargs) -> (pd.DataFrame, dict):
    col_name = kwargs['col_name']
    fin_df = kwargs['fin_data']['financial_data']
    finance = fin_df.copy()
    finance['net_profit_ttm'] = finance['R_np@xbx'].rolling(4, min_periods=4).sum()
    df_temp = df.copy()
    df_temp['net_profit_ttm'] = finance['net_profit_ttm'].reindex(df_temp.index, method='ffill')
    df_temp[col_name] = df_temp['total_market_cap'] / df_temp['net_profit_ttm']
    df_temp[col_name] = df_temp[col_name].replace([float('inf'), -float('inf')], pd.NA)
    df_temp.loc[df_temp['net_profit_ttm'] <= 0, col_name] = pd.NA
    agg_rules = {col_name: 'last'}
    return (df_temp[[col_name]], agg_rules)
