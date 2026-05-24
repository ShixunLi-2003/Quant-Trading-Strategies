"""Resolve configured factor names to their implementation modules."""

from __future__ import annotations

import importlib

import pandas as pd


FACTOR_MODULE_MAP = {
    "Volume Contraction Factor": "volume_contraction_factor",
    "Turnover Rate": "turnover_rate",
    "Long-Term Low Volume": "long_term_low_volume",
    "Oversold": "oversold",
    "Net Capital Inflow": "net_capital_inflow",
    "Rolling PE": "rolling_pe",
}


class FactorInterface:
    """Minimal factor interface shared by all factor modules."""

    fin_cols = []

    @staticmethod
    def add_factor(df: pd.DataFrame, param=None, **kwargs) -> tuple[pd.DataFrame, dict]:
        col_name = kwargs["col_name"]
        return df[[col_name]], {col_name: "last"}

    def add_factors(self, df: pd.DataFrame, params=(), **kwargs) -> tuple[pd.DataFrame, dict]:
        raise NotImplementedError


class FactorHub:
    """Load factor modules lazily and keep them cached."""

    _factor_cache: dict[str, type] = {}

    @staticmethod
    def get_by_name(factor_name: str) -> FactorInterface:
        if factor_name in FactorHub._factor_cache:
            return FactorHub._factor_cache[factor_name]

        module_suffix = FACTOR_MODULE_MAP.get(factor_name, factor_name.lower().replace(" ", "_"))
        module_name = f"factor_library.{module_suffix}"

        try:
            factor_module = importlib.import_module(module_name)
            factor_content = {
                name: getattr(factor_module, name)
                for name in dir(factor_module)
                if not name.startswith("__")
            }
            factor_content.setdefault("fin_cols", [])
            factor_instance = type(module_suffix, (), factor_content)
            FactorHub._factor_cache[factor_name] = factor_instance
            return factor_instance
        except ModuleNotFoundError as exc:
            raise ValueError(f"Factor {factor_name} not found.") from exc
