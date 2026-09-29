from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import numpy as np


@dataclass(frozen=True)
class TrainingConfig:
    payload: Dict[str, Any]

    @classmethod
    def load(cls, path: str) -> "TrainingConfig":
        config = cls(json.loads(Path(path).read_text(encoding="utf-8")))
        config.validate()
        return config

    def validate(self) -> None:
        p = self.payload
        train_days = int(p.get("train_days", 40))
        max_train_days = int(p.get("max_train_days", 42))
        if not 1 <= train_days <= max_train_days <= 42:
            raise ValueError("require 1 <= train_days <= max_train_days <= 42")
        for key in ("validation_days", "test_days", "step_days"):
            if int(p.get(key, 0)) <= 0:
                raise ValueError(key + " must be positive")
        if int(p.get("embargo_days", 0)) < 0:
            raise ValueError("embargo_days cannot be negative")
        if p.get("mode") not in {"probe", "debug", "train"}:
            raise ValueError("mode must be probe, debug or train")
        objective = p.get("objective", {
            "primary": "total_net_return", "secondary": "max_drawdown"})
        if objective.get("primary") != "total_net_return":
            raise ValueError("objective.primary must be total_net_return")
        if objective.get("secondary") != "max_drawdown":
            raise ValueError("objective.secondary must be max_drawdown")
        if float(p.get("initial_capital_usd", 10000)) != 10000.0:
            raise ValueError("initial_capital_usd is fixed at 10000")
        if not 1 <= int(p.get("selection_top_n", 5)) <= 100:
            raise ValueError("selection_top_n must be between 1 and 100")
        for key in ("entry_slippage_bps", "exit_slippage_bps", "commission_bps",
                    "minimum_commission_usd", "limit_buffer"):
            if float(p.get(key, 0)) < 0:
                raise ValueError(key + " cannot be negative")
        if int(p.get("platform_subscription_limit", 100)) != 100:
            raise ValueError("platform_subscription_limit must match the verified account limit 100")
        if p.get("universe_policy") == "nasdaq100_one_security_per_company":
            context = list(p.get("market_context", [])) + list(p.get("sector_context", []))
            if context:
                raise ValueError(
                    "Nasdaq-100 platform preset reserves all 100 subscription slots for stocks")
        fundamentals = p.get("fundamentals", {})
        if fundamentals and not isinstance(fundamentals, dict):
            raise ValueError("fundamentals must be an object")
        if fundamentals.get("enabled", False) and not fundamentals.get("path"):
            raise ValueError("fundamentals.path is required when fundamentals are enabled")
        coverage = float(fundamentals.get("minimum_coverage", 0.0))
        if not 0.0 <= coverage <= 1.0:
            raise ValueError("fundamentals.minimum_coverage must be between 0 and 1")
        if fundamentals.get("enabled", False):
            if fundamentals.get("strict_point_in_time", True) is not True:
                raise ValueError("strict_point_in_time cannot be disabled")
            if float(fundamentals.get("availability_lag_hours", 24)) < 0:
                raise ValueError("availability_lag_hours cannot be negative")
            if not isinstance(fundamentals.get("feature_columns", []), list):
                raise ValueError("fundamentals.feature_columns must be a list")
        model_entrypoint = p.get("model_entrypoint", "")
        model_name = p.get("model_name", "")
        if model_entrypoint:
            if ":" not in model_entrypoint:
                raise ValueError("model_entrypoint must be module:Class")
        elif not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(model_name)):
            raise ValueError("model_name must match a Python module in models/")
        dataset_columns = p.get("dataset_columns", ["*"])
        if not isinstance(dataset_columns, list) or not dataset_columns:
            raise ValueError("dataset_columns must be a non-empty list")
        if len(dataset_columns) != len(set(dataset_columns)):
            raise ValueError("dataset_columns contains duplicates")

    def __getattr__(self, name: str) -> Any:
        if name == "model_entrypoint" and "model_entrypoint" not in self.payload:
            return "models.{}:Model".format(self.payload["model_name"])
        try:
            return self.payload[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def load_model(entrypoint: str, params: Dict[str, Any]):
    module_name, class_name = entrypoint.split(":", 1)
    model_class = getattr(importlib.import_module(module_name), class_name)
    model = model_class(**params)
    missing = [name for name in ("fit", "predict", "save")
               if not callable(getattr(model, name, None))]
    if missing:
        raise TypeError("model missing methods: " + ", ".join(missing))
    return model


def checked_predict(model, features: np.ndarray) -> np.ndarray:
    values = np.asarray(model.predict(features), dtype=float).reshape(-1)
    if len(values) != len(features):
        raise ValueError("model output length mismatch")
    if not np.isfinite(values).all():
        raise ValueError("model returned non-finite scores")
    return values
