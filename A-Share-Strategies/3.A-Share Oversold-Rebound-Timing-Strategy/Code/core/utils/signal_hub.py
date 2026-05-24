"""Resolve configured timing-signal names to signal modules."""

from __future__ import annotations

import importlib


SIGNAL_MODULE_MAP = {
    "Volume Expansion Moving Average Timing": "volume_expansion_moving_average_timing",
    "Volume Expansion Timing": "volume_expansion_timing",
    "Moving Average Timing": "moving_average_timing",
}


def get_signal_by_name(name: str) -> dict:
    """Load a signal module and return its callable contents."""
    module_suffix = SIGNAL_MODULE_MAP.get(name, name.lower().replace(" ", "_"))
    module_name = f"signal_library.{module_suffix}"
    try:
        signal_module = importlib.import_module(module_name)
        return {
            attr_name: getattr(signal_module, attr_name)
            for attr_name in dir(signal_module)
            if not attr_name.startswith("__") and callable(getattr(signal_module, attr_name))
        }
    except ModuleNotFoundError as exc:
        raise ValueError(f"Signal {name} not found.") from exc
