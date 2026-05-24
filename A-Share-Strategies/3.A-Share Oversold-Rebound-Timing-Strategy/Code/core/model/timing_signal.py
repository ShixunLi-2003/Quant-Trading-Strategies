"""Equity-timing model wiring for the strategy framework."""

from dataclasses import dataclass, field
from typing import Callable, Dict
import pandas as pd
from core.model.strategy_config import parse_param
from core.utils.signal_hub import get_signal_by_name

@dataclass
class EquityTiming:
    name: str
    params: list | tuple = ()
    funcs: Dict[str, Callable] = field(default_factory=dict)

    @classmethod
    def init(cls, **config) -> 'EquityTiming':
        config['params'] = parse_param(config.get('params', ()))
        config['funcs'] = get_signal_by_name(config['name'])
        leverage_signal = cls(**config)
        return leverage_signal

    def get_equity_signal(self, equity_df: pd.DataFrame) -> pd.Series:
        return self.funcs['equity_signal'](equity_df, *self.params)
