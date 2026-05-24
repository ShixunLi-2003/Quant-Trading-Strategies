"""Resolve strategy display names to optional extension modules."""

from __future__ import annotations

import importlib


STRATEGY_MODULE_MAP = {
    "Oversold Rebound Timing Strategy": "custom_strategy",
    "Limit-Up Breakout Timing Strategy": "custom_strategy",
}


def get_strategy_by_name(name: str) -> dict:
    """Load an optional strategy module and return its callables."""
    module_suffix = STRATEGY_MODULE_MAP.get(name)
    if module_suffix is None:
        return {}

    module_name = f"strategy_library.{module_suffix}"
    try:
        strategy_module = importlib.import_module(module_name)
        return {
            attr_name: getattr(strategy_module, attr_name)
            for attr_name in dir(strategy_module)
            if not attr_name.startswith("__") and callable(getattr(strategy_module, attr_name))
        }
    except ModuleNotFoundError:
        return {}
