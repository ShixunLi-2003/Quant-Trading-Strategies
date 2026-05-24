"""Load factor implementations dynamically from the local factor library."""

from __future__ import annotations

import importlib

import pandas as pd


class DummyFactor:
    """Type hint placeholder for dynamically loaded factor modules."""

    def signal(self, *args) -> pd.DataFrame:
        raise NotImplementedError


class FactorHub:
    """Cache dynamically imported factor modules by factor name."""

    _factor_cache: dict[str, DummyFactor] = {}

    @staticmethod
    def get_by_name(factor_name: str) -> DummyFactor:
        if factor_name in FactorHub._factor_cache:
            return FactorHub._factor_cache[factor_name]

        try:
            factor_module = importlib.import_module(f"factors.{factor_name}")
            factor_content = {
                name: getattr(factor_module, name)
                for name in dir(factor_module)
                if not name.startswith("__")
            }
            factor_instance = type(factor_name, (), factor_content)
            FactorHub._factor_cache[factor_name] = factor_instance
            return factor_instance
        except ModuleNotFoundError as exc:
            raise ValueError(f"Factor {factor_name} not found.") from exc
        except AttributeError as exc:
            raise ValueError(f"Error loading factor module {factor_name}.") from exc
