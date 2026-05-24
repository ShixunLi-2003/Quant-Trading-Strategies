"""Active strategy rules and factor-combination logic."""

import pandas as pd
from core.model.strategy_config import StrategyConfig

def filter_stock(df, strategy: StrategyConfig) -> pd.DataFrame:
    return df

def calc_select_factor(df, strategy: StrategyConfig) -> pd.DataFrame:
    return pd.DataFrame({strategy.factor_name: strategy.calc_select_factor_default(df)}, index=df.index)
